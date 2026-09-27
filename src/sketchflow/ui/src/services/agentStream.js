/**
 * SketchFlow SSE Streaming & API Service
 * Consumes real-time LangGraph streaming telemetry over Server-Sent Events.
 */

export async function parseSSEStream(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';

    for (const part of parts) {
      if (!part.trim()) continue;
      const lines = part.split('\n');
      let eventType = 'message';
      let dataStr = '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.substring(7).trim();
        } else if (line.startsWith('data: ')) {
          dataStr = line.substring(6).trim();
        }
      }

      if (dataStr) {
        try {
          const parsed = JSON.parse(dataStr);
          onEvent(eventType, parsed);
        } catch (e) {
          console.warn('Failed to parse SSE JSON payload:', dataStr, e);
        }
      }
    }
  }
}

export async function startAgentStream({
  imageBase64 = null,
  imagePath = null,
  preferredProvider = 'nvidia',
  threadId = null,
  onEvent,
  onError
}) {
  try {
    const response = await fetch('/api/v1/agent/run-stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        image_base64: imageBase64,
        image_path: imagePath,
        preferred_provider: preferredProvider,
        thread_id: threadId
      })
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || 'Failed to start agent stream');
    }

    await parseSSEStream(response, onEvent);
  } catch (err) {
    if (onError) onError(err);
    else console.error('Agent stream error:', err);
  }
}

export async function resumeAgentStream({
  threadId,
  humanApproved = true,
  customParameters = null,
  onEvent,
  onError
}) {
  try {
    const response = await fetch('/api/v1/agent/resume-stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        thread_id: threadId,
        human_approved: humanApproved,
        custom_parameters: customParameters
      })
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || 'Failed to resume agent stream');
    }

    await parseSSEStream(response, onEvent);
  } catch (err) {
    if (onError) onError(err);
    else console.error('Resume stream error:', err);
  }
}

export async function checkSystemHealth() {
  try {
    const res = await fetch('/api/v1/health');
    if (!res.ok) return { healthy: false };
    return await res.json();
  } catch (e) {
    return { healthy: false, error: e.message };
  }
}

export async function testWebhookLive({ webhookUrl, payload = { test: true, timestamp: Date.now() } }) {
  const pathSlug = webhookUrl ? webhookUrl.split('/').pop() : 'test';
  const res = await fetch('/api/v1/deploy/test-webhook', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      webhook_path: pathSlug,
      payload: payload,
      method: 'POST'
    })
  });
  return await res.json();
}
