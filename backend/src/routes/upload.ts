import { Router, Request, Response } from 'express';
import multer from 'multer';
import * as fs from 'fs';
import * as path from 'path';
// @ts-ignore - pdf-parse doesn't have types
import pdf from 'pdf-parse';
import { vectorStore } from '../services/vectorStore';
import { v4 as uuidv4 } from 'uuid';

const router = Router();

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = path.join(__dirname, '../../storage');
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir, { recursive: true });
    }
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    cb(null, `${Date.now()}-${file.originalname}`);
  },
});

const upload = multer({ storage });

// POST /api/upload-kb - Upload PDF and chunk it
router.post('/kb', upload.single('file'), async (req: Request, res: Response) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const filePath = req.file.path;
    const fileBuffer = fs.readFileSync(filePath);

    // Parse PDF
    const pdfData = await pdf(fileBuffer);
    const text = pdfData.text;

    // Simple chunking (split by paragraphs, max 1000 chars per chunk)
    const chunks = text
      .split(/\n\s*\n/)
      .map((chunk: string) => chunk.trim())
      .filter((chunk: string) => chunk.length > 50)
      .flatMap((chunk: string) => {
        if (chunk.length <= 1000) return [chunk];
        // Split large chunks
        const subChunks: string[] = [];
        for (let i = 0; i < chunk.length; i += 1000) {
          subChunks.push(chunk.substring(i, i + 1000));
        }
        return subChunks;
      });

    // Store chunks in vector store
    const chunkIds = [];
    for (let i = 0; i < chunks.length; i++) {
      const chunkId = uuidv4();
      await vectorStore.addDocument(chunkId, chunks[i], {
        type: 'kb',
        source: req.file.originalname,
        created_at: new Date().toISOString(),
      });
      chunkIds.push(chunkId);
    }

    res.json({
      success: true,
      filename: req.file.originalname,
      chunks: chunks.length,
      chunkIds,
    });
  } catch (error) {
    console.error('Error uploading KB:', error);
    res.status(500).json({ error: 'Failed to process PDF' });
  }
});

export default router;

