import { Tag } from "../ui";
export function LockStatus({
  status,
}: {
  status: "pending" | "on_time" | "late" | "unknown";
}) {
  const labels = {
    pending: "Team Lock pendiente",
    on_time: "Team Lock a tiempo",
    late: "Team Lock tardío",
    unknown: "Team Lock fijado · horario sin evidencia",
  };
  return <Tag>{labels[status]}</Tag>;
}
