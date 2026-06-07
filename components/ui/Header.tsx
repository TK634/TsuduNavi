"use client";

import { ReactNode } from "react";

interface HeaderProps {
  title: string;
  right?: ReactNode;
}

export function Header({ title, right }: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 bg-navy-500 text-white px-4 py-3 flex items-center justify-between shadow-md">
      <h1 className="text-base font-bold tracking-wide">{title}</h1>
      {right && <div>{right}</div>}
    </header>
  );
}
