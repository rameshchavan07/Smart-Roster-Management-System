import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

const ROUTE_LABELS: Record<string, string> = {
  '': 'Dashboard',
  roster: 'Roster Workspace',
  conflicts: 'Conflicts',
  leaves: 'Leaves & Comp-offs',
  team: 'Team & Pods',
  brands: 'Brands & Processes',
  reports: 'Reports & Export',
  settings: 'Settings & Audit',
  'design-system': 'Design System',
};

export const Breadcrumbs: React.FC = () => {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter((x) => x);

  return (
    <nav aria-label="Breadcrumb" className="flex items-center text-xs">
      <ol className="flex items-center gap-1.5 text-ink-3">
        <li className="flex items-center">
          <Link
            to="/"
            className="flex items-center gap-1 text-ink-3 hover:text-ink transition-colors font-medium"
            title="Dashboard"
          >
            <Home className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">RosterOps</span>
          </Link>
        </li>

        {pathnames.length === 0 ? (
          <li className="flex items-center gap-1.5">
            <ChevronRight className="h-3 w-3 text-border-strong shrink-0" />
            <span className="font-semibold text-ink" aria-current="page">
              Dashboard
            </span>
          </li>
        ) : (
          pathnames.map((segment, index) => {
            const routeTo = `/${pathnames.slice(0, index + 1).join('/')}`;
            const isLast = index === pathnames.length - 1;
            const label = ROUTE_LABELS[segment] || segment;

            return (
              <li key={routeTo} className="flex items-center gap-1.5">
                <ChevronRight className="h-3 w-3 text-border-strong shrink-0" />
                {isLast ? (
                  <span className="font-semibold text-ink" aria-current="page">
                    {label}
                  </span>
                ) : (
                  <Link
                    to={routeTo}
                    className="text-ink-3 hover:text-ink transition-colors font-medium"
                  >
                    {label}
                  </Link>
                )}
              </li>
            );
          })
        )}
      </ol>
    </nav>
  );
};

