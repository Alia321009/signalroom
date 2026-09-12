import { useEffect, useRef, useState } from "react";

/** True for ~700ms whenever `value` changes, then false again. Does not
 * flash on mount -- only on a genuine change. */
export function useFlashOnChange(value: unknown): boolean {
  const [flashing, setFlashing] = useState(false);
  const prev = useRef(value);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (prev.current === value) return;
    prev.current = value;
    setFlashing(true);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setFlashing(false), 700);
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [value]);

  return flashing;
}
