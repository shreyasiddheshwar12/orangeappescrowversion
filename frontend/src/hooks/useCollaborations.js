import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { campaignAPI, getErrorMessage } from '../lib/api';

/**
 * Loads the viewer's collaborations (sent and received) and exposes every
 * lifecycle action the existing API supports. Each action refreshes the lists.
 */
export default function useCollaborations() {
  const [incoming, setIncoming] = useState([]);
  const [outgoing, setOutgoing] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);

  const refresh = useCallback(async () => {
    const [inRes, outRes] = await Promise.all([campaignAPI.getIncoming(), campaignAPI.getOutgoing()]);
    setIncoming(inRes.data);
    setOutgoing(outRes.data);
    return { incoming: inRes.data, outgoing: outRes.data };
  }, []);

  useEffect(() => {
    refresh().catch(() => {}).finally(() => setLoading(false));
  }, [refresh]);

  const all = useMemo(() => {
    const incomingIds = new Set(incoming.map((c) => c.id));
    return [
      ...incoming.map((c) => ({ ...c, _incoming: true })),
      ...outgoing.filter((c) => !incomingIds.has(c.id)).map((c) => ({ ...c, _incoming: false })),
    ].sort((a, b) => (b.updatedAt || '').localeCompare(a.updatedAt || ''));
  }, [incoming, outgoing]);

  const run = useCallback(async (key, fn, success) => {
    setBusy(key);
    try {
      const res = await fn();
      const message = typeof success === 'function' ? success(res) : success;
      if (message) toast.success(message);
      await refresh();
      return res;
    } catch (error) {
      toast.error(getErrorMessage(error, 'Something went wrong'));
      return null;
    } finally {
      setBusy(null);
    }
  }, [refresh]);

  const actions = useMemo(() => ({
    create: (payload) => run('create', () => campaignAPI.create(payload), 'Request sent'),
    accept: (c) => run(`accept:${c.id}`, () => campaignAPI.respond(c.id, 'accept'), 'Request accepted'),
    decline: (c) => run(`decline:${c.id}`, () => campaignAPI.respond(c.id, 'reject'), 'Request declined'),
    pay: (c) => run(`pay:${c.id}`, () => campaignAPI.pay(c.id), (res) => res?.data?.message || 'Payment confirmed'),
    ship: (c, details) => run(`ship:${c.id}`, () => campaignAPI.addShipping(c.id, details), 'Shipping details added'),
    receive: (c) => run(`receive:${c.id}`, () => campaignAPI.confirmReceipt(c.id), 'Receipt confirmed'),
    submit: (c, link) => run(`submit:${c.id}`, () => campaignAPI.submitLink(c.id, link), 'Content submitted for review'),
    verify: (c) => run(`verify:${c.id}`, () => campaignAPI.verifyLink(c.id), (res) => res?.data?.message || 'Content approved'),
    complete: (c) => run(`complete:${c.id}`, () => campaignAPI.complete(c.id), (res) => res?.data?.message || 'Collaboration completed'),
    rate: (c, rating, feedback) => run(`rate:${c.id}`, () => campaignAPI.rate(c.id, rating, feedback), 'Thanks for the rating'),
    report: (c, reason) => run(`report:${c.id}`, () => campaignAPI.report(c.id, reason), 'Reported. Orange will review it.'),
  }), [run]);

  return { incoming, outgoing, all, loading, busy, refresh, actions };
}
