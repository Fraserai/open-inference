/**
 * API documentation.
 *
 * Model IDs and the base URL are rendered from live configuration so the docs
 * cannot drift from the registry.
 */

import type { Metadata } from "next";
import { PRODUCT, apiBaseUrl } from "@/lib/config";
import { CATALOGUE, INTELLIGENCE_SCORE_SOURCE } from "@/lib/registry/catalogue";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: `API documentation — ${PRODUCT.name}`,
  description: "Authentication, models, chat completions, streaming and migration.",
};

export default function Docs() {
  const base = apiBaseUrl();

  return (
    <div className="wrap doclayout">
      <nav className="docnav">
        <div className="grp">Getting started</div>
        <a href="#overview">Overview</a>
        <a href="#base-url">Base URL</a>
        <a href="#authentication">Authentication</a>
        <a href="#models">Model IDs</a>
        <div className="grp">API reference</div>
        <a href="#list-models">List models</a>
        <a href="#chat">Chat completions</a>
        <a href="#streaming">Streaming</a>
        <a href="#errors">Errors</a>
        <a href="#residency">Residency headers</a>
        <div className="grp">Guides</div>
        <a href="#sdk">JavaScript &amp; Python</a>
        <a href="#migration">Migrating from OpenAI</a>
        <a href="#sovereignty">Sovereignty model</a>
      </nav>

      <article className="doc">
        <h2 id="overview">Overview</h2>
        <p>
          {PRODUCT.name} serves five open-weight models from Australian infrastructure through
          one OpenAI-compatible API. The weights are stored in Australia, inference runs on
          Australian compute, and requests are never routed to an overseas inference provider.
        </p>
        <p>
          You need three things: an API key, our base URL, and one of our five model IDs. If
          your application already speaks the OpenAI chat completions format, that is the whole
          migration.
        </p>

        <h2 id="base-url">Base URL</h2>
        <pre>
          <code>{base}</code>
        </pre>
        <p>
          All endpoints are versioned under <code>/v1</code>. The current endpoints are{" "}
          <code>GET /v1/models</code>, <code>GET /v1/models/{"{model}"}</code>,{" "}
          <code>POST /v1/chat/completions</code> and <code>GET /v1/health</code>.
        </p>

        <h2 id="authentication">Authentication</h2>
        <p>
          Send your key as a bearer token. Keys look like{" "}
          <code>coral_sk_...</code> and are shown once at creation — we store only a hash, so a
          lost key is replaced rather than recovered.
        </p>
        <pre>
          <code>{`Authorization: Bearer coral_sk_YOUR_KEY`}</code>
        </pre>
        <p>
          You never need credentials for the underlying Australian compute provider. Your key
          authenticates you to {PRODUCT.name}; we hold the infrastructure credentials.
        </p>
        <div className="notice">
          <b>Keep keys server-side.</b> A key in browser or mobile client code is a published
          key. Proxy requests through your own backend.
        </div>

        <h2 id="models">Model IDs</h2>
        <table>
          <thead>
            <tr>
              <th>Model ID</th>
              <th>Name</th>
              <th>Intelligence score</th>
            </tr>
          </thead>
          <tbody>
            {CATALOGUE.map((m) => (
              <tr key={m.apiModelId}>
                <td>
                  <code>{m.apiModelId}</code>
                </td>
                <td>{m.displayName}</td>
                <td>{m.intelligenceScore}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p style={{ fontSize: 13 }}>
          Intelligence scores are published by {INTELLIGENCE_SCORE_SOURCE.name} (
          <a href={INTELLIGENCE_SCORE_SOURCE.url} target="_blank" rel="noreferrer noopener">
            {INTELLIGENCE_SCORE_SOURCE.url}
          </a>
          ) and reproduced as catalogue metadata. They are not {PRODUCT.name} benchmarks.
        </p>

        <h2 id="list-models">List models</h2>
        <p>
          Returns the catalogue with deployment and sovereignty metadata. Upstream endpoints and
          provider credentials are never included.
        </p>
        <pre>
          <code>{`curl ${base}/models \\
  -H "Authorization: Bearer $CORAL_API_KEY"`}</code>
        </pre>
        <h3>Response</h3>
        <pre>
          <code>{`{
  "object": "list",
  "data": [
    {
      "id": "kimi-k3",
      "object": "model",
      "owned_by": "Coral",
      "display_name": "Kimi K3",
      "creator": null,
      "intelligence_score": {
        "value": 60,
        "source": "Artificial Analysis",
        "source_url": "https://artificialanalysis.ai",
        "note": "Intelligence scores are published by Artificial Analysis ..."
      },
      "model_version": null,
      "context_window": null,
      "modalities": ["text"],
      "available": true,
      "deployment": {
        "status": "active",
        "infrastructure_provider": "firmus",
        "infrastructure_region": "au-syd-1",
        "inference_country": "AU",
        "weight_country": "AU",
        "weight_location": "firmus:au-syd-1:coral-weight-vault/kimi-k3"
      },
      "sovereignty": {
        "status": "verified",
        "australian_sovereign": true,
        "label": "Australian sovereign — verified",
        "verified_at": "2026-09-01",
        "verified_by": "...",
        "verification_method": "..."
      }
    }
  ]
}`}</code>
        </pre>
        <p>
          <code>creator</code>, <code>model_version</code> and <code>context_window</code> are{" "}
          <code>null</code> until a deployment supplies them. We publish nulls rather than
          guesses.
        </p>

        <h2 id="chat">Chat completions</h2>
        <pre>
          <code>{`curl ${base}/chat/completions \\
  -H "Authorization: Bearer $CORAL_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "kimi-k3",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Summarise the Privacy Act in two sentences."}
    ],
    "temperature": 0.7,
    "max_tokens": 512
  }'`}</code>
        </pre>
        <h3>Parameters</h3>
        <table>
          <thead>
            <tr>
              <th>Field</th>
              <th>Type</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>model</code></td>
              <td>string</td>
              <td>Required. One of the five model IDs above.</td>
            </tr>
            <tr>
              <td><code>messages</code></td>
              <td>array</td>
              <td>Required. At least one message.</td>
            </tr>
            <tr>
              <td><code>stream</code></td>
              <td>boolean</td>
              <td>Server-sent events when true.</td>
            </tr>
            <tr>
              <td><code>max_tokens</code></td>
              <td>integer</td>
              <td>Also accepts <code>max_completion_tokens</code>.</td>
            </tr>
            <tr>
              <td><code>temperature</code>, <code>top_p</code></td>
              <td>number</td>
              <td>Standard sampling controls.</td>
            </tr>
            <tr>
              <td><code>stop</code>, <code>seed</code>, <code>n</code></td>
              <td>mixed</td>
              <td>Passed through to the inference server.</td>
            </tr>
          </tbody>
        </table>
        <p>
          Parameters we do not interpret are forwarded to the Australian inference server, so
          engine-specific options continue to work.
        </p>

        <h2 id="streaming">Streaming</h2>
        <p>
          Set <code>&quot;stream&quot;: true</code>. The response is a{" "}
          <code>text/event-stream</code> of OpenAI-format chunks terminated by{" "}
          <code>data: [DONE]</code>.
        </p>
        <pre>
          <code>{`curl -N ${base}/chat/completions \\
  -H "Authorization: Bearer $CORAL_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"glm-5.3","messages":[{"role":"user","content":"Hello"}],"stream":true}'`}</code>
        </pre>
        <pre>
          <code>{`data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Hel"}}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"lo"}}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":9,"completion_tokens":2,"total_tokens":11}}

data: [DONE]`}</code>
        </pre>
        <p>
          Token usage arrives on the final chunk so streamed requests are metered without our
          reading any of the content.
        </p>

        <h2 id="errors">Errors</h2>
        <p>Errors use the OpenAI error envelope, so existing client libraries surface them.</p>
        <pre>
          <code>{`{
  "error": {
    "message": "The model \\"gpt-4\\" does not exist. Available models: kimi-k3, glm-5.3, qwen-3.8, inkling, nemotron-3-ultra.",
    "type": "not_found_error",
    "param": "model",
    "code": "model_not_found"
  }
}`}</code>
        </pre>
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>Type</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>400</td>
              <td><code>invalid_request_error</code></td>
              <td>Malformed JSON or a parameter that failed validation.</td>
            </tr>
            <tr>
              <td>401</td>
              <td><code>authentication_error</code></td>
              <td>Missing, invalid or revoked API key.</td>
            </tr>
            <tr>
              <td>404</td>
              <td><code>not_found_error</code></td>
              <td>Unknown model ID.</td>
            </tr>
            <tr>
              <td>502</td>
              <td><code>api_error</code></td>
              <td>The Australian inference server returned an error.</td>
            </tr>
            <tr>
              <td>503</td>
              <td><code>sovereignty_error</code></td>
              <td>
                No Australian deployment available for that model. The request was not sent
                anywhere else.
              </td>
            </tr>
          </tbody>
        </table>
        <div className="notice">
          <b>503 is not a retry-elsewhere signal.</b> A <code>sovereignty_error</code> means the
          Australian deployment could not serve the request. We do not have an offshore
          fallback, by design. Retry against {PRODUCT.name} or fail your own request.
        </div>

        <h2 id="residency">Residency headers</h2>
        <p>Every chat completion response carries where it was served.</p>
        <table>
          <thead>
            <tr>
              <th>Header</th>
              <th>Meaning</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>x-request-id</code></td>
              <td>Correlates with our usage records.</td>
            </tr>
            <tr>
              <td><code>x-coral-deployment</code></td>
              <td>Which Australian deployment served it.</td>
            </tr>
            <tr>
              <td><code>x-coral-inference-country</code></td>
              <td>Always <code>AU</code> for a real deployment.</td>
            </tr>
            <tr>
              <td><code>x-coral-inference-region</code></td>
              <td>Provider region, e.g. <code>au-syd-1</code>.</td>
            </tr>
            <tr>
              <td><code>x-coral-sovereignty</code></td>
              <td>
                <code>verified</code>, <code>configured_unverified</code> or{" "}
                <code>development_mock</code>.
              </td>
            </tr>
            <tr>
              <td><code>x-coral-development-mock</code></td>
              <td>Present only when a development mock produced the response.</td>
            </tr>
          </tbody>
        </table>

        <h2 id="sdk">JavaScript &amp; Python</h2>
        <p>
          Use the official OpenAI SDKs — only the base URL and key change. Nothing below is
          {PRODUCT.name}-specific beyond those two lines.
        </p>
        <div className="codecols">
          <div>
            <h3>TypeScript</h3>
            <pre>
              <code>{`import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "${base}",
  apiKey: process.env.CORAL_API_KEY,
});

const res = await client.chat.completions.create({
  model: "kimi-k3",
  messages: [{ role: "user", content: "Hello" }],
});

console.log(res.choices[0].message.content);

// Streaming
const stream = await client.chat.completions.create({
  model: "kimi-k3",
  messages: [{ role: "user", content: "Hello" }],
  stream: true,
});

for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta?.content ?? "");
}`}</code>
            </pre>
          </div>
          <div>
            <h3>Python</h3>
            <pre>
              <code>{`import os
from openai import OpenAI

client = OpenAI(
    base_url="${base}",
    api_key=os.environ["CORAL_API_KEY"],
)

res = client.chat.completions.create(
    model="kimi-k3",
    messages=[{"role": "user", "content": "Hello"}],
)
print(res.choices[0].message.content)

# Streaming
stream = client.chat.completions.create(
    model="kimi-k3",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")`}</code>
            </pre>
          </div>
        </div>

        <h3>Fetch, without an SDK</h3>
        <pre>
          <code>{`const res = await fetch("${base}/chat/completions", {
  method: "POST",
  headers: {
    "Authorization": \`Bearer \${process.env.CORAL_API_KEY}\`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    model: "qwen-3.8",
    messages: [{ role: "user", content: "Hello" }],
  }),
});

console.log(res.headers.get("x-coral-inference-country")); // AU
console.log(await res.json());`}</code>
        </pre>

        <h2 id="migration">Migrating from OpenAI</h2>
        <div className="migrate">
          <div className="step">
            <div className="step-n">STEP 01</div>
            <h4>Change the base URL</h4>
            <p>
              Point your client at <code>{base}</code>.
            </p>
          </div>
          <div className="step">
            <div className="step-n">STEP 02</div>
            <h4>Change the API key</h4>
            <p>
              Swap <code>OPENAI_API_KEY</code> for your <code>CORAL_API_KEY</code>.
            </p>
          </div>
          <div className="step">
            <div className="step-n">STEP 03</div>
            <h4>Choose a model</h4>
            <p>Replace the model string with one of our five model IDs.</p>
          </div>
        </div>
        <pre>
          <code>{`- const client = new OpenAI({
-   baseURL: "https://api.openai.com/v1",
-   apiKey: process.env.OPENAI_API_KEY,
- });
+ const client = new OpenAI({
+   baseURL: "${base}",
+   apiKey: process.env.CORAL_API_KEY,
+ });

- model: "gpt-4o",
+ model: "kimi-k3",`}</code>
        </pre>
        <h3>Differences to expect</h3>
        <ul>
          <li>
            Only the five model IDs above are valid. There is no aliasing of OpenAI model names.
          </li>
          <li>
            Endpoints beyond models and chat completions are not implemented in this MVP —
            no embeddings, images, audio or assistants.
          </li>
          <li>
            A <code>503 sovereignty_error</code> is possible where OpenAI would have retried in
            another region. That is deliberate.
          </li>
          <li>
            Responses carry <code>x-coral-*</code> residency headers your client will ignore
            safely.
          </li>
        </ul>

        <h2 id="sovereignty">Sovereignty model</h2>
        <p>Every model in the registry reports one of four states:</p>
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>Meaning</th>
              <th>Serves traffic</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>verified</code></td>
              <td>
                Australian inference and weight storage configured, and verification recorded
                (who, when, how).
              </td>
              <td>Yes</td>
            </tr>
            <tr>
              <td><code>configured_unverified</code></td>
              <td>Australian deployment configured, verification not yet performed.</td>
              <td>Yes</td>
            </tr>
            <tr>
              <td><code>development_mock</code></td>
              <td>A local stub. No GPU, no weights, no sovereignty claim.</td>
              <td>Non-production only</td>
            </tr>
            <tr>
              <td><code>not_configured</code></td>
              <td>
                No deployment, or a deployment that failed Australian validation and was
                rejected.
              </td>
              <td>No</td>
            </tr>
          </tbody>
        </table>
        <p>
          Only <code>verified</code> sets <code>australian_sovereign: true</code>. A model
          existing in the catalogue is never, by itself, a sovereignty claim.
        </p>
      </article>
    </div>
  );
}
