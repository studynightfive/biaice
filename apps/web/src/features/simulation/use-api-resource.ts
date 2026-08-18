"use client";

import { useCallback, useEffect, useState } from "react";

export function useApiResource<T>(loader: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);

  const refresh = useCallback(async () => {
    try {
      setData(await loader());
      setError(null);
    } catch (caught) {
      setError(caught);
    }
  }, [loader]);

  useEffect(() => {
    let cancelled = false;
    void loader().then(
      (nextData) => {
        if (cancelled) return;
        setData(nextData);
        setError(null);
      },
      (caught: unknown) => {
        if (!cancelled) setError(caught);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [loader]);

  return { data, error, refresh } as const;
}
