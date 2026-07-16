// Componente de ejemplo — patrón usado en toda la app real para
// consumir la API del backend y mostrar el estado de riesgo de un estudiante.
// No es el componente final (ver frontend/README.md).

"use client";

import { useEffect, useState } from "react";

type SRDResponse = {
  estudiante_id: number;
  score: number;
  nivel: "CRÍTICO" | "MODERADO" | "LEVE" | "SIN RIESGO";
  factores: string[];
};

const colorPorNivel: Record<string, string> = {
  "CRÍTICO": "bg-red-100 text-red-800 border-red-300",
  "MODERADO": "bg-yellow-100 text-yellow-800 border-yellow-300",
  "LEVE": "bg-blue-100 text-blue-800 border-blue-300",
  "SIN RIESGO": "bg-green-100 text-green-800 border-green-300",
};

export default function ExampleCard({ estudianteId }: { estudianteId: number }) {
  const [data, setData] = useState<SRDResponse | null>(null);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/srd/${estudianteId}`)
      .then((res) => res.json())
      .then(setData)
      .catch(() => setData(null));
  }, [estudianteId]);

  if (!data) return <div className="p-4 text-sm text-gray-400">Cargando...</div>;

  return (
    <div className={`rounded-xl border p-4 shadow-sm ${colorPorNivel[data.nivel]}`}>
      <p className="text-xs uppercase tracking-wide">Score de Riesgo de Deserción</p>
      <p className="text-2xl font-bold">{Math.round(data.score * 100)}%</p>
      <p className="text-sm font-medium">{data.nivel}</p>
      <ul className="mt-2 list-disc pl-4 text-xs">
        {data.factores.map((f) => (
          <li key={f}>{f}</li>
        ))}
      </ul>
    </div>
  );
}
