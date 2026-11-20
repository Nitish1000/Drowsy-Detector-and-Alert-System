async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

export const listSessions = () => request('/sessions');
export const startSession = () => request('/sessions/start', { method: 'POST' });
export const stopSession = (id) => request(`/sessions/${id}/stop`, { method: 'POST' });
export const deleteSession = (id) => request(`/sessions/${id}`, { method: 'DELETE' });
