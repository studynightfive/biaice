import Link from "next/link";
import type { ComponentProps } from "react";
import type { ButtonVariant } from "./button";
import styles from "./ui.module.css";

type LinkButtonProps = ComponentProps<typeof Link> & {
  variant?: ButtonVariant;
  disabled?: boolean;
};

export function LinkButton({
  className,
  variant = "primary",
  disabled = false,
  tabIndex,
  ...props
}: LinkButtonProps) {
  return (
    <Link
      aria-disabled={disabled || undefined}
      className={[styles.linkButton, styles[variant], className].filter(Boolean).join(" ")}
      tabIndex={disabled ? -1 : tabIndex}
      {...props}
    />
  );
}
