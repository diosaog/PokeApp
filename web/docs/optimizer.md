# Optimizador

El optimizador recibe un `OptimizationRequest` con Pokemon, objetivo, perfil, inventario, presupuesto y modo de busqueda.

## Flujo

1. Genera parejas posibles.
2. Valida compatibilidad.
3. Determina descendencia.
4. Genera planes de objetos utiles.
5. Compara sexo aleatorio contra sexo forzado si el objetivo lo requiere.
6. Calcula costes y descarta acciones inviables por presupuesto o inventario.
7. Estima probabilidad directa y valor como reproductor intermedio.
8. Separa acciones dominadas.
9. Devuelve recomendacion, alternativas y advertencias.

## Limites actuales

La version actual recomienda el siguiente intento y explora una profundidad acotada para valorar utilidad intermedia. No demuestra optimalidad global de todo el arbol multigeneracional.
