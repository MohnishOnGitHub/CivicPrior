export default function BricsPanel() {
  return (
    <section>
      <div className="page-head">
        <div>
          <h2>BRICS / Digital Public Good</h2>
          <p>
            A shared CivicPrior layer for schemas, APIs, and allocation
            interfaces. Country adapters stay local. This is an architecture
            demonstration, not a live government integration.
          </p>
        </div>
      </div>

      <div className="callout ok">
        Digital Public Good architecture — demonstration
      </div>
      <div className="callout mock-note">
        Raw citizen submissions stay in the jurisdiction that collected them.
        The shared layer exchanges schemas, aggregates, and optionally model
        updates — not raw personal records.
      </div>

      <div className="dpg-layers">
        <article className="card dpg-layer shared">
          <h3>Shared CivicPrior layer</h3>
          <p className="muted">Portable contracts. Same in every adapter.</p>
          <ul>
            <li>Common citizen-request schema</li>
            <li>Common infrastructure taxonomy</li>
            <li>Common API contract</li>
            <li>Versioned scoring / optimization interfaces</li>
            <li>Model / aggregate exchange format</li>
          </ul>
        </article>
        <article className="card dpg-layer local">
          <h3>Country / jurisdiction layer</h3>
          <p className="muted">Stays local. Never required to cross borders.</p>
          <ul>
            <li>Local citizen submissions</li>
            <li>Local languages</li>
            <li>Local public datasets</li>
            <li>Local policy weights / constraints</li>
            <li>Local privacy / governance rules</li>
          </ul>
        </article>
      </div>

      <div className="dpg-flow card">
        <h3>What may be exchanged</h3>
        <ol className="dpg-steps">
          <li>
            <strong>Local intake</strong>
            <span>Citizen text stays in-country</span>
          </li>
          <li>
            <strong>Normalize</strong>
            <span>Map to the common schema</span>
          </li>
          <li>
            <strong>Aggregate</strong>
            <span>Clusters, evidence scores, portfolios</span>
          </li>
          <li>
            <strong>Optional share</strong>
            <span>Schema versions, aggregates, model updates</span>
          </li>
        </ol>
        <p className="muted">
          No claim that raw personal data must move between BRICS countries.
        </p>
      </div>

      <div className="section">
        <h3>Illustrative country adapters</h3>
        <p className="muted">
          Examples only. CivicPrior does not connect to real government systems
          in this demo.
        </p>
        <div className="adapter-grid">
          <article className="card">
            <h4>India</h4>
            <p className="muted">Illustrative adapter</p>
            <p>
              Hindi / Telugu / English requests map onto the common CivicPrior
              schema already used by citizen intake.
            </p>
            <p>
              <strong>Local stay:</strong> original wording, phone numbers if
              collected, raw audio.
            </p>
            <p>
              <strong>Shared contract:</strong> category, geography, urgency,
              requested intervention.
            </p>
          </article>
          <article className="card">
            <h4>Brazil</h4>
            <p className="muted">Illustrative adapter</p>
            <p>
              A Portuguese complaint uses the same extraction contract and
              lands in the same structured fields.
            </p>
            <p>
              <strong>Local stay:</strong> the Portuguese original and any
              municipal identifiers.
            </p>
            <p>
              <strong>Shared contract:</strong> the same water / healthcare /
              roads taxonomy.
            </p>
          </article>
          <article className="card">
            <h4>South Africa</h4>
            <p className="muted">Illustrative adapter</p>
            <p>
              A local public-dataset adapter publishes population, clinic
              access, and investment-gap fields through the common evidence
              interface.
            </p>
            <p>
              <strong>Local stay:</strong> source tables and household-level
              records.
            </p>
            <p>
              <strong>Shared contract:</strong> normalized deficit, equity, and
              investment-gap scores.
            </p>
          </article>
        </div>
      </div>

      <div className="section">
        <h3>Interoperability walk-through</h3>
        <div className="interop-examples">
          <article className="card">
            <div className="label">India</div>
            <p>Local language request → CivicPrior common schema</p>
            <p className="muted">
              Example: a Hindi Ward 17 water complaint becomes{" "}
              <code>category=water</code>, <code>geo_id=geo_ward_17</code>,{" "}
              <code>requested_intervention=water_distribution_upgrade</code>.
            </p>
          </article>
          <article className="card">
            <div className="label">Brazil</div>
            <p>Portuguese request → same common schema</p>
            <p className="muted">
              Example: “a água chega só dois dias por semana” normalizes to
              English and the same water / supply-reliability fields. No raw
              text is required by the shared layer.
            </p>
          </article>
          <article className="card">
            <div className="label">South Africa</div>
            <p>Local dataset adapter → same infrastructure evidence interface</p>
            <p className="muted">
              Example: a clinic-catchment table is mapped to{" "}
              <code>infrastructure_deficit</code>, <code>equity</code>, and{" "}
              <code>investment_gap</code>. Scoring and the optimizer stay
              unchanged.
            </p>
          </article>
        </div>
      </div>
    </section>
  );
}
