import type { ReactNode } from "react";

/** One content hierarchy for task pages; actions retain their existing permissions. */
export function PageHeader({ title, description, context, action }: { title: string; description?: string; context?: string; action?: ReactNode }) {
  return <header className="page-header">
    <div className="min-w-0">{context && <p className="page-context">{context}</p>}<h1 className="page-title">{title}</h1>{description && <p className="page-description">{description}</p>}</div>
    {action && <div className="page-header-action">{action}</div>}
  </header>;
}
