# Perfiles de servidor

El perfil inicial esta en `src/rules/diosesmon/profile.ts`.

## Diosesmon

Valores confirmados:

- `breedingBaseCost`: 2500
- `breedingDurationMinutes`: 25
- `forcedSexCost`: 5000
- `defaultItemPrice`: 500
- `purchasesTakeTimeMinutes`: 0

## Crear otro perfil

1. Copia `profile.ts`.
2. Cambia `economy`, `time`, `inheritance` y `offspring`.
3. Declara cada regla como confirmada, pendiente o configurable.
4. Evita excepciones en componentes React; usa datos declarativos.
