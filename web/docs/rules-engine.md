# Motor de reglas

El motor vive fuera de React para que las reglas no dependan de la interfaz.

## Modulos

- `engine/compatibility/canBreed.ts`: valida disponibilidad, proteccion, esterilidad, Ditto, grupos huevo y sexo.
- `engine/offspring/getOffspringSpecies.ts`: determina especie, madre y padre cuando es posible.
- `engine/economy/costs.ts`: calcula desembolso real, coste de reposicion y consumo de inventario.
- `engine/inheritance/probability.ts`: enumera patrones de herencia y calcula probabilidad de objetivo.
- `engine/scheduling/schedule.ts`: estima tiempo del siguiente intento con ranuras y enfriamiento configurado.

## Honestidad

Las reglas pendientes se modelan como configuracion del perfil. Si una regla no esta confirmada, el resultado incluye advertencias y la UI no lo presenta como exactitud demostrada.
