import { AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";

export function TeamLockWarning({ own = false }: { own?: boolean }) {
  return (
    <div role="alert" className="notice">
      <AlertTriangle size={24} aria-hidden="true" />
      <div>
        <strong>
          {own
            ? "Tu Team Lock está pendiente."
            : "Falta el Team Lock de este entrenador."}
        </strong>
        <p>
          No hay un equipo fijado para esta jornada. El equipo del save no lo
          sustituye. Puedes continuar en la Liga; revisa el Team Lock antes de
          combatir.
        </p>
        {own && <Link to="/battle">Revisar Team Preview →</Link>}
      </div>
    </div>
  );
}
