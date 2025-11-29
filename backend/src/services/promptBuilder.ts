import * as fs from 'fs';
import * as path from 'path';
import * as zlib from 'zlib';
import { pool } from '../db';
import { query } from '../clients/vectorstore';

const MAX_PROMPT_TOKENS = parseInt(process.env.MAX_PROMPT_TOKENS || '4000', 10); // Reduced from 8000
const MAX_CHUNK_SIZE = 300; // Reduced from 500 for faster processing
const MAX_STORED_PROMPT_LENGTH = 4000;

// Rough token estimation (1 token ≈ 4 characters)
function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

function sanitizeText(text: string): string {
  // Remove control characters except newlines and tabs
  return text
    .replace(/[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]/g, '')
    .trim();
}

function truncateText(text: string, maxTokens: number): string {
  const maxChars = maxTokens * 4;
  if (text.length <= maxChars) return text;
  return text.substring(0, maxChars - 3) + '...';
}

export class PromptBuilder {
  private tone: 'formal' | 'warm' | 'crisp';
  private contactName: string;
  private contactCompany?: string;
  private threadMessages: Array<{ sender: string; body: string; created_at: string }>;
  private retrievedContext: string[] = [];
  private retrievedIds: string[] = [];

  constructor(
    tone: 'formal' | 'warm' | 'crisp',
    contactName: string,
    contactCompany?: string
  ) {
    this.tone = tone;
    this.contactName = contactName;
    this.contactCompany = contactCompany;
    this.threadMessages = [];
  }

  addThreadMessages(messages: Array<{ sender: string; body: string; created_at: string }>) {
    // Take last 2 messages (reduced from 3 for speed), sanitize
    this.threadMessages = messages
      .slice(-2)
      .map((msg) => ({
        ...msg,
        body: sanitizeText(msg.body).substring(0, 500), // Reduced from 1000 for faster processing
      }));
  }

  async addRetrievedContext(queryText: string, k: number = 2) {
    // Reduced from 3 to 2 for faster RAG retrieval
    const results = await query(queryText, k);
    this.retrievedIds = results.map((r) => r.id);
    this.retrievedContext = results.map((r) => sanitizeText(r.text).substring(0, 300)); // Reduced from 500
  }

  build(): { promptString: string; metadata: any } {
    // Load template
    const templatePath = path.join(__dirname, '../../prompts/assistant_template.md');
    let template = '';
    try {
      template = fs.readFileSync(templatePath, 'utf-8');
    } catch (error) {
      template = `You are an AI assistant helping manage communications.

Tone: {{tone}}
Contact: {{contactName}}{{#contactCompany}} from {{contactCompany}}{{/contactCompany}}

{{#retrievedContext}}
Relevant context:
{{#each retrievedContext}}
- {{this}}
{{/each}}
{{/retrievedContext}}

Conversation history:
{{#each threadMessages}}
[{{sender}}]: {{body}}
{{/each}}

Generate a {{tone}} reply to the latest message.`;
    }

    // Build base prompt
    let prompt = template
      .replace(/\{\{tone\}\}/g, this.tone)
      .replace(/\{\{contactName\}\}/g, this.contactName)
      .replace(/\{\{contactCompany\}\}/g, this.contactCompany || '');

    // Add retrieved context
    if (this.retrievedContext.length > 0) {
      prompt += '\n\nRelevant context from knowledge base:\n';
      this.retrievedContext.forEach((ctx, idx) => {
        prompt += `${idx + 1}. ${ctx}\n`;
      });
    }

    // Add conversation history (concise format)
    prompt += '\n\nHistory:\n';
    this.threadMessages.forEach((msg) => {
      prompt += `${msg.sender}: ${msg.body}\n`;
    });

    prompt += `\n\nWrite a natural, human reply in a ${this.tone} tone. No templates, no corporate speak - just respond like a real person would.`;

    // Truncate if needed
    const estimatedTokens = estimateTokens(prompt);
    if (estimatedTokens > MAX_PROMPT_TOKENS) {
      const contextTokens = estimateTokens(
        this.retrievedContext.join('\n') + this.threadMessages.map((m) => m.body).join('\n')
      );
      const baseTokens = estimateTokens(prompt) - contextTokens;
      const availableTokens = MAX_PROMPT_TOKENS - baseTokens;

      // Truncate context proportionally
      if (availableTokens > 0) {
        const contextRatio = availableTokens / contextTokens;
        this.retrievedContext = this.retrievedContext.map((ctx) =>
          truncateText(ctx, Math.floor(estimateTokens(ctx) * contextRatio))
        );
        this.threadMessages = this.threadMessages.map((msg) => ({
          ...msg,
          body: truncateText(msg.body, Math.floor(estimateTokens(msg.body) * contextRatio)),
        }));

        // Rebuild with truncated content
        prompt = this.build().promptString;
      } else {
        prompt = truncateText(prompt, MAX_PROMPT_TOKENS);
      }
    }

    const metadata = {
      tone: this.tone,
      contactName: this.contactName,
      contactCompany: this.contactCompany,
      threadMessageCount: this.threadMessages.length,
      retrievedChunkCount: this.retrievedContext.length,
      estimatedTokens: estimateTokens(prompt),
      retrievedIds: this.retrievedIds,
    };

    return { promptString: sanitizeText(prompt), metadata };
  }

  static async buildForMessage(
    messageId: string,
    tone: 'formal' | 'warm' | 'crisp' = 'warm'
  ): Promise<{ prompt: string; retrievedIds: string[]; metadata: any }> {
    // Get message and contact
    const messageResult = await pool.query(
      `SELECT m.*, c.name as contact_name, c.company as contact_company
       FROM messages m
       JOIN contacts c ON m.contact_id = c.id
       WHERE m.id = $1`,
      [messageId]
    );

    if (messageResult.rows.length === 0) {
      throw new Error('Message not found');
    }

    const message = messageResult.rows[0];
    const threadId = message.thread_id;

    // Get thread messages
    const threadResult = await pool.query(
      `SELECT sender, body, created_at
       FROM messages
       WHERE thread_id = $1
       ORDER BY created_at ASC`,
      [threadId]
    );

    // Build prompt
    const builder = new PromptBuilder(
      tone,
      message.contact_name,
      message.contact_company
    );
    builder.addThreadMessages(threadResult.rows);

    // Retrieve context (reduced to 2 for speed)
    const queryText = threadResult.rows
      .slice(-2) // Only use last 2 messages for RAG query
      .map((m: any) => m.body.substring(0, 200)) // Truncate query text
      .join(' ');
    await builder.addRetrievedContext(queryText, 2); // Reduced from 3

    const { promptString, metadata } = builder.build();

    return {
      prompt: promptString,
      retrievedIds: builder['retrievedIds'],
      metadata,
    };
  }
}

export async function storePrompt(
  suggestionId: string,
  promptString: string
): Promise<string> {
  // Store truncated version in DB
  const truncated = promptString.substring(0, MAX_STORED_PROMPT_LENGTH);
  await pool.query(`UPDATE suggestions SET prompt = $1 WHERE id = $2`, [
    truncated,
    suggestionId,
  ]);

  // Store gzipped full version
  const promptsDir = path.join(__dirname, '../../storage/prompts');
  if (!fs.existsSync(promptsDir)) {
    fs.mkdirSync(promptsDir, { recursive: true });
  }

  const gzipPath = path.join(promptsDir, `suggestion-${suggestionId}.gz`);
  const compressed = zlib.gzipSync(promptString);
  fs.writeFileSync(gzipPath, compressed);

  return gzipPath;
}
