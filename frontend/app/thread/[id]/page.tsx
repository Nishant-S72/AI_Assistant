/**
 * Thread Page
 * Individual thread view with messages and suggestion panel
 */

'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import ThreadView from '@/components/ThreadView';
import ContextPanel from '@/components/ContextPanel';
import { api } from '@/lib/api';

export default function ThreadPage() {
  const params = useParams();
  const id = params.id as string;
  const [contact, setContact] = useState<any>(null);
  const [tasks, setTasks] = useState<any[]>([]);

  useEffect(() => {
    // Load contact and tasks when thread loads
    const loadContext = async () => {
      try {
        const threadData = await api.getMessage(id);
        setContact(threadData.contact);
        
        if (threadData.contact.id) {
          const taskData = await api.getTasks();
          setTasks(taskData.filter((t) => t.contact_id === threadData.contact.id));
        }
      } catch (error) {
        console.error('Error loading context:', error);
      }
    };
    if (id) {
      loadContext();
    }
  }, [id]);

  if (!id) {
    return <div>Loading...</div>;
  }

  return (
    <div className="flex h-full">
      <div className="flex-1">
        <ThreadView messageId={id} />
      </div>
      <ContextPanel contact={contact} tasks={tasks} />
    </div>
  );
}
