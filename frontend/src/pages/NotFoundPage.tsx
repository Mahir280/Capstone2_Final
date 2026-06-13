import { Link } from "react-router-dom";

import { PageHeader } from "../components/common/PageHeader";

export function NotFoundPage() {
  return (
    <section>
      <PageHeader
        eyebrow="Navigation"
        title="Page not found"
        description="The requested workspace page does not exist."
      />
      <div className="card">
        <Link className="link-button" to="/">
          ← Return to Overview
        </Link>
      </div>
    </section>
  );
}
