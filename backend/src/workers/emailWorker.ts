import { Worker, Queue } from 'bullmq';
import IORedis from 'ioredis';
import { pool } from '../db';

// Configure Redis with BullMQ requirements
const redisOptions: any = {
  maxRetriesPerRequest: null, // Required by BullMQ
};

let connection: IORedis;
try {
  if (process.env.REDIS_URL) {
    connection = new IORedis(process.env.REDIS_URL, redisOptions);
  } else {
    connection = new IORedis({
      host: 'localhost',
      port: 6379,
      ...redisOptions,
    });
  }
} catch (error) {
  console.warn('⚠️  Redis connection failed, email worker will not start');
  // Create a dummy connection that will fail gracefully
  connection = new IORedis({ host: 'localhost', port: 6379, ...redisOptions, lazyConnect: true });
}

export interface EmailJob {
  messageId: string;
  contactId: string;
  to: string;
  subject: string;
  body: string;
}

export const emailQueue = new Queue<EmailJob>('email', { connection });

// Worker to process email jobs
export function startEmailWorker() {
  try {
    // Test Redis connection
    connection.ping().catch(() => {
      throw new Error('Redis not available');
    });
  } catch (error) {
    console.warn('⚠️  Redis not available, skipping email worker');
    return null;
  }

  const worker = new Worker<EmailJob>(
    'email',
    async (job) => {
      const { messageId, to, subject, body } = job.data;

      console.log(`📧 Processing email job for message ${messageId}`);

      // Simulate email sending
      // TODO: Replace with actual Gmail API integration
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Log the event
      await pool.query(
        `INSERT INTO events (type, payload) VALUES ($1, $2)`,
        [
          'email_sent',
          JSON.stringify({
            messageId,
            to,
            subject,
            simulated: true,
          }),
        ]
      );

      console.log(`✅ Email sent (simulated) to ${to}`);
    },
    { connection }
  );

  worker.on('completed', (job) => {
    console.log(`✅ Email job ${job.id} completed`);
  });

  worker.on('failed', (job, err) => {
    console.error(`❌ Email job ${job?.id} failed:`, err);
  });

  console.log('📧 Email worker started');
  return worker;
}

