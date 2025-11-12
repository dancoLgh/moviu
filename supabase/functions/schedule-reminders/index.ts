import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
);

type ReminderPayload = {
  tenant_id: string;
  entry_id: string;
  member_id: string;
  start_ts: string;
};

export default async function handler(): Promise<Response> {
  const windowTs = new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString();
  const { data, error } = await supabase.rpc('get_upcoming_entries', { until_ts: windowTs });

  if (error) {
    return new Response(JSON.stringify({ ok: false, error: error.message }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  const reminders = (data as ReminderPayload[] | null) ?? [];

  for (const reminder of reminders) {
    await supabase.from('notifications').insert({
      tenant_id: reminder.tenant_id,
      user_id: reminder.member_id,
      type: 'push',
      template_key: 'class_reminder',
      payload: { entry_id: reminder.entry_id, start_ts: reminder.start_ts },
      status: 'queued'
    });
  }

  return new Response(JSON.stringify({ ok: true, queued: reminders.length }), {
    headers: { 'Content-Type': 'application/json' }
  });
}

Deno.serve(handler);
