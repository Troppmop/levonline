import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

type Direction = "ltr" | "rtl";

const STORAGE_KEY = "layout_direction";

interface DirectionContextValue {
  direction: Direction;
  toggleDirection: () => void;
  setDirection: (dir: Direction) => void;
}

const DirectionContext = createContext<DirectionContextValue | undefined>(undefined);

function readStoredDirection(): Direction {
  return localStorage.getItem(STORAGE_KEY) === "rtl" ? "rtl" : "ltr";
}

export function DirectionProvider({ children }: { children: React.ReactNode }) {
  const [direction, setDirectionState] = useState<Direction>(readStoredDirection);

  useEffect(() => {
    document.documentElement.dir = direction;
    localStorage.setItem(STORAGE_KEY, direction);
  }, [direction]);

  const setDirection = useCallback((dir: Direction) => setDirectionState(dir), []);
  const toggleDirection = useCallback(
    () => setDirectionState((prev) => (prev === "ltr" ? "rtl" : "ltr")),
    []
  );

  return (
    <DirectionContext.Provider value={{ direction, toggleDirection, setDirection }}>
      {children}
    </DirectionContext.Provider>
  );
}

export function useDirection(): DirectionContextValue {
  const ctx = useContext(DirectionContext);
  if (!ctx) throw new Error("useDirection must be used within a DirectionProvider");
  return ctx;
}
