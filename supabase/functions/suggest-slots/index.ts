import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
);

export default async function handler(req: Request): Promise<Response> {
  try {
    const { tenant_id, service_id, from, to } = await req.json();
    const { data, error } = await supabase
      .from('class_occurrences')
      .select('id,start_ts,end_ts,capacity,booked_count,professional_id,status')
      .eq('tenant_id', tenant_id)
      .eq('service_id', service_id)
      .gte('start_ts', from)
      .lte('end_ts', to)
      .eq('status', 'scheduled');

    if (error) {
      return new Response(JSON.stringify({ ok: false, error: error.message }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const available = (data ?? []).filter((occ) => occ.booked_count < occ.capacity);

    return new Response(JSON.stringify({ ok: true, slots: available }), {
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
