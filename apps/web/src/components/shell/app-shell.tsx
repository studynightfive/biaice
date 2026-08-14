"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { StatusBadge } from "@/components/ui";
import {
  buildUnitPath,
  UNIT_ROUTE_GROUPS,
  UNIT_ROUTES,
} from "@/lib/navigation/unit-routes";
import styles from "./shell.module.css";

type AppShellProps = {
  children: ReactNode;
  projectId: string;
  unitId: string;
};

export function AppShell({ children, projectId, unitId }: AppShellProps) {
  const pathname = usePathname();
  const currentRoute = UNIT_ROUTES.find((route) => pathname.endsWith(route.suffix));

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar} aria-label="当前决策单元导航">
        <div className={styles.contextCard}>
          <span className={styles.contextLabel}>CURRENT DECISION UNIT</span>
          <strong>项目 / 决策单元上下文</strong>
          <StatusBadge tone="info">合成数据模式</StatusBadge>
          <code>
            {projectId} / {unitId}
          </code>
        </div>
        <nav className={styles.navigation} aria-label="决策单元阶段导航">
          {UNIT_ROUTE_GROUPS.map((group) => (
            <section className={styles.navGroup} key={group.id} aria-label={group.label}>
              <h2 className={styles.navGroupTitle}>{group.label}</h2>
              <ul className={styles.navList}>
                {UNIT_ROUTES.filter((route) => route.group === group.id).map((route) => {
                  const href = buildUnitPath(projectId, unitId, route.suffix);
                  const isActive = pathname === href;

                  return (
                    <li key={route.suffix}>
                      <Link
                        aria-current={isActive ? "page" : undefined}
                        className={[styles.navLink, isActive && styles.navLinkActive]
                          .filter(Boolean)
                          .join(" ")}
                        href={href}
                      >
                        <span>{route.shortLabel}</span>
                        <small>M{route.owner}</small>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </nav>
      </aside>

      <div className={styles.content}>
        <nav aria-label="面包屑">
          <ol className={styles.breadcrumbs}>
            <li>
              <Link href="/projects">项目</Link>
            </li>
            <li>
              <Link href={`/projects/${encodeURIComponent(projectId)}`}>{projectId}</Link>
            </li>
            <li>
              <Link href={`/projects/${encodeURIComponent(projectId)}/units`}>{unitId}</Link>
            </li>
            <li aria-current="page">{currentRoute?.label ?? "决策工作区"}</li>
          </ol>
        </nav>
        <main>{children}</main>
      </div>
    </div>
  );
}
