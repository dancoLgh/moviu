import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
);

export default async function handler(req: Request): Promise<Response> {
  try {
    const { tenant_id, occurrence_id, reason } = await req.json();
    await supabase
      .from('class_occurrences')
      .update({ status: 'cancelled', cancel_reason: reason ?? 'Sin especificar' })
      .eq('tenant_id', tenant_id)
      .eq('id', occurrence_id);

    const { data: entries } = await supabase
      .from('subscription_entries')
      .select('id, subscription_id')
      .eq('tenant_id', tenant_id)
      .eq('class_occurrence_id', occurrence_id);

    if (entries?.length) {
      await supabase
        .from('subscription_entries')
        .update({ status: 'cancelled' })
        .in('id', entries.map((e) => e.id));
    }

    return new Response(JSON.stringify({ ok: true, cancelled: entries?.length ?? 0 }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    return new Response(JSON.stringify({ ok: false, error: String(error) }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

Deno.serve(handler);
