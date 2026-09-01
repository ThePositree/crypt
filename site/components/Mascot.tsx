type MascotProps = {
  mood?: "reader" | "builder" | "search" | "risk";
  label?: string;
};

export function Mascot({ mood = "reader", label }: MascotProps) {
  return (
    <div className={`mascot mascot-${mood}`} aria-hidden="true">
      <div className="mascot-face">
        <span />
        <span />
      </div>
      <div className="mascot-note">{label}</div>
    </div>
  );
}
