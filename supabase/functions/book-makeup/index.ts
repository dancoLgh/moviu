import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
);

export default async function handler(req: Request): Promise<Response> {
  try {
    const { tenant_id, subscription_id, target_occurrence_id } = await req.json();
    const today = new Date();
    const monthKey = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), 1))
      .toISOString()
      .slice(0, 10);

    const { data: makeup } = await supabase
      .from('makeups')
      .select('*')
      .eq('tenant_id', tenant_id)
      .eq('subscription_id', subscription_id)
      .eq('month', monthKey)
      .maybeSingle();

    if (!makeup || makeup.used >= makeup.allowed) {
      return new Response(JSON.stringify({ ok: false, error: 'No hay recuperos disponibles' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const { data: occurrence } = await supabase
      .from('class_occurrences')
      .select('*')
      .eq('tenant_id', tenant_id)
      .eq('id', target_occurrence_id)
      .eq('status', 'scheduled')
      .maybeSingle();

    if (!occurrence || occurrence.booked_count >= occurrence.capacity) {
      return new Response(JSON.stringify({ ok: false, error: 'Sin cupo disponible' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const { error: insertError } = await supabase.from('subscription_entries').insert({
      tenant_id,
      subscription_id,
      class_occurrence_id: target_occurrence_id,
      status: 'scheduled',
      source: 'makeup'
    });

    if (insertError) {
      return new Response(JSON.stringify({ ok: false, error: insertError.message }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    await supabase
      .from('makeups')
      .update({ used: makeup.used + 1 })
      .eq('id', makeup.id);

    await supabase
      .from('class_occurrences')
      .update({ booked_count: occurrence.booked_count + 1 })
      .eq('id', occurrence.id);

    return new Response(JSON.stringify({ ok: true }), {
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
