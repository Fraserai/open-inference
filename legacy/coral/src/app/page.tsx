/**
 * Landing page.
 *
 * Sovereignty status shown here is read live from the registry. A model is
 * labelled "Australian sovereign" only when its deployment is configured AND
 * verified. Anything else is shown as what it actually is.
 */

import { PRODUCT, apiBaseUrl } from "@/lib/config";
import { INTELLIGENCE_SCORE_SOURCE, listPublicModels, type PublicModel } from "@/lib/registry";

export const dynamic = "force-dynamic";

const STATUS_UI: Record<
  PublicModel["sovereignty"]["status"],
  { dot: string; text: string }
> = {
  verified: { dot: "dot-verified", text: "Australian sovereign · verified" },
  configured_unverified: { dot: "dot-pending", text: "AU deployment · verification pending" },
  development_mock: { dot: "dot-mock", text: "Development mock · not sovereign" },
  not_configured: { dot: "dot-none", text: "Deployment not configured" },
};

function ModelRow({ model }: { model: PublicModel }) {
  const ui = STATUS_UI[model.sovereignty.status];
  const region = model.deployment.infrastructure_region;
  const provider = model.deployment.infrastructure_provider;

  return (
    <div className="model-row">
      <div>
        <div className="model-name">{model.display_name}</div>
        <div className="model-id">{model.id}</div>
      </div>
      <div className="score">
        <span className="score-val">{model.intelligence_score.value}</span>
        <span className="score-bar">
          <span
            className="score-fill"
            style={{ width: `${Math.min(100, model.intelligence_score.value)}%` }}
          />
        </span>
      </div>
      <div>
        <span className="status">
          <span className={`dot ${ui.dot}`} aria-hidden />
          {ui.text}
        </span>
      </div>
      <div className="deploy">
        {provider && region ? `${provider} · ${region}` : "—"}
      </div>
    </div>
  );
}

export default function Home() {
  const models = listPublicModels(PRODUCT.name);
  const base = apiBaseUrl();
  const verified = models.filter((m) => m.sovereignty.australian_sovereign).length;

  return (
    <main>
      <div className="hero">
        <div className="wrap">
          <div className="eyebrow">Australian sovereign AI infrastructure</div>
          <h1>Open weights. Australian compute. One API.</h1>
          <p className="lede">
            Five open-weight models with their weights <strong>stored in Australia</strong>,
            running on <strong>Australian AI compute</strong>, served to Australian businesses
            and enterprises through a single OpenAI-compatible API. No request is ever routed
            offshore.
          </p>
          <div className="btnrow">
            <a className="btn btn-primary" href="/docs">
              Read the API docs
            </a>
            <a className="btn" href="#models">
              See the five models
            </a>
          </div>
        </div>
      </div>

      <div className="pillars">
        <div className="pillar">
          <h3>Weights</h3>
          <p>
            <b>Downloaded and stored in Australia</b>
            We hold the open weights ourselves on Australian storage.
          </p>
        </div>
        <div className="pillar">
          <h3>Compute</h3>
          <p>
            <b>Australian GPUs</b>
            Inference executes on machines physically located in Australia.
          </p>
        </div>
        <div className="pillar">
          <h3>API</h3>
          <p>
            <b>One Australian endpoint</b>
            Change your base URL and key. Keep your existing code.
          </p>
        </div>
        <div className="pillar">
          <h3>Customers</h3>
          <p>
            <b>Australian businesses</b>
            Built for enterprises with data residency obligations.
          </p>
        </div>
      </div>

      <section id="models">
        <div className="wrap">
          <h2>Five open-weight models</h2>
          <p className="section-sub">
            The catalogue is deliberately small. Each model has exactly one Australian
            deployment, and the status below is read live from the model registry — not a
            marketing claim.
          </p>

          <div className="models">
            <div className="model-head">
              <div>Model</div>
              <div>Intelligence score</div>
              <div>Sovereignty status</div>
              <div>Deployment</div>
            </div>
            {models.map((m) => (
              <ModelRow key={m.id} model={m} />
            ))}
          </div>

          <div className="attribution">
            Intelligence scores are published by{" "}
            <a href={INTELLIGENCE_SCORE_SOURCE.url} rel="noreferrer noopener" target="_blank">
              {INTELLIGENCE_SCORE_SOURCE.name}
            </a>{" "}
            and reproduced here as catalogue metadata. They are not {PRODUCT.name} benchmarks
            and are not measured by {PRODUCT.name}.
          </div>

          {verified === 0 && (
            <div className="notice">
              <b>No verified Australian deployment is connected in this environment.</b> The
              models above are serving from development mocks or are unconfigured. Sovereignty
              is only claimed once a deployment has been configured on Australian
              infrastructure and verified.
            </div>
          )}
        </div>
      </section>

      <section id="sovereignty">
        <div className="wrap">
          <h2>Sovereignty is enforced in code, not promised in copy</h2>
          <p className="section-sub">
            A model only becomes routable when its deployment declares Australian inference and
            Australian weight storage. A deployment that fails that check is rejected at
            configuration load and can never receive traffic.
          </p>

          <div className="migrate">
            <div className="step">
              <div className="step-n">CONTROL 01</div>
              <h4>Australian-only routing</h4>
              <p>
                Each model resolves to exactly one Australian deployment. There is no fallback
                list and no offshore provider configured anywhere in the codebase.
              </p>
            </div>
            <div className="step">
              <div className="step-n">CONTROL 02</div>
              <h4>Fail loudly, never silently</h4>
              <p>
                If the Australian endpoint is unreachable, the request returns 503 and says so.
                It is not retried in another country.
              </p>
            </div>
            <div className="step">
              <div className="step-n">CONTROL 03</div>
              <h4>Verified means verified</h4>
              <p>
                Sovereign status requires a recorded verification — who checked, when, and how.
                Existing in the catalogue proves nothing.
              </p>
            </div>
            <div className="step">
              <div className="step-n">CONTROL 04</div>
              <h4>Per-request evidence</h4>
              <p>
                Every response carries the deployment, region and inference country in its
                headers, so residency is auditable per call.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="wrap">
          <h2>Migrate in three lines</h2>
          <p className="section-sub">
            The API is OpenAI-compatible. Point your existing client at {PRODUCT.name}, swap the
            key, and choose one of our five model IDs.
          </p>
          <pre>
            <code>
              <span className="c-cmt">{"# Before"}</span>
              {"\n"}client = OpenAI(base_url=<span className="c-str">
                &quot;https://api.openai.com/v1&quot;
              </span>, api_key=OPENAI_KEY){"\n"}
              {"\n"}
              <span className="c-cmt">{"# After"}</span>
              {"\n"}client = OpenAI(base_url=<span className="c-str">
                &quot;{base}&quot;
              </span>, api_key=CORAL_KEY){"\n"}
              {"\n"}client.chat.completions.<span className="c-fn">create</span>({"\n"}
              {"    "}model=<span className="c-str">&quot;kimi-k3&quot;</span>,{"\n"}
              {"    "}messages=[{"{"}<span className="c-str">&quot;role&quot;</span>:{" "}
              <span className="c-str">&quot;user&quot;</span>,{" "}
              <span className="c-str">&quot;content&quot;</span>:{" "}
              <span className="c-str">&quot;Hello&quot;</span>{"}"}],{"\n"}
              {")"}
            </code>
          </pre>
          <div className="btnrow" style={{ marginTop: 24 }}>
            <a className="btn btn-primary" href="/docs">
              Full documentation
            </a>
          </div>
        </div>
      </section>
    </main>
  );
}
