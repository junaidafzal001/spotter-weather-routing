import { Truck } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-[1600px] items-center justify-center gap-2.5 px-4 py-2.5 lg:px-6">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-white shadow-sm">
          <Truck size={18} aria-hidden />
        </span>
        <h1 className="text-sm font-bold leading-tight tracking-tight text-ink">
          Spotter Route Weather
        </h1>
      </div>
    </header>
  );
}
