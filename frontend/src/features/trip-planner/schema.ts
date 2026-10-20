import { z } from "zod";

export const tripFormSchema = z.object({
  origin: z
    .string()
    .min(2, "Enter an origin city, address, or postal code")
    .max(200, "Origin is too long"),
  destination: z
    .string()
    .min(2, "Enter a destination city, address, or postal code")
    .max(200, "Destination is too long"),
  departure: z.string().min(1, "Choose a departure date and time"),
  loadWeight: z
    .number({ message: "Enter the load weight in pounds" })
    .int("Enter whole pounds")
    .min(0, "Load weight cannot be negative")
    .max(80_000, "Maximum supported load weight is 80,000 lb"),
  interval: z.union([z.literal(10), z.literal(25), z.literal(50)]),
});

export type FormValues = z.infer<typeof tripFormSchema>;
