import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { InventoryCategory, InventoryItem, InventoryLocation } from "../types";

const LOCATIONS: { value: InventoryLocation; label: string }[] = [
  { value: "floor_1_kitchen", label: "Floor 1 Kitchen" },
  { value: "floor_2_kitchen", label: "Floor 2 Kitchen" },
  { value: "floor_3_kitchen", label: "Floor 3 Kitchen" },
  { value: "basement", label: "Basement" },
];

const CATEGORIES: { value: InventoryCategory; label: string }[] = [
  { value: "perishable", label: "Perishable" },
  { value: "non_perishable", label: "Non-perishable" },
  { value: "cleaning_supplies", label: "Cleaning supplies" },
  { value: "paper_goods", label: "Paper goods" },
  { value: "other", label: "Other" },
];

export default function Inventory() {
  const [items, setItems] = useState<InventoryItem[] | null>(null);
  const [locationFilter, setLocationFilter] = useState<InventoryLocation | "">("");

  const [name, setName] = useState("");
  const [category, setCategory] = useState<InventoryCategory>("non_perishable");
  const [location, setLocation] = useState<InventoryLocation>("floor_1_kitchen");
  const [unit, setUnit] = useState("unit");
  const [quantity, setQuantity] = useState("0");
  const [threshold, setThreshold] = useState("0");

  async function load() {
    const query = locationFilter ? `?location=${locationFilter}` : "";
    const data = await api.get<InventoryItem[]>(`/inventory${query}`);
    setItems(data);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locationFilter]);

  async function adjust(itemId: string, delta: number) {
    await api.post(`/inventory/${itemId}/adjust`, {
      change_quantity: delta,
      reason: delta > 0 ? "restock" : "consumption",
    });
    load();
  }

  async function createItem(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    await api.post("/inventory", {
      name,
      category,
      location,
      unit,
      quantity: Number(quantity) || 0,
      low_stock_threshold: Number(threshold) || 0,
    });
    setName("");
    setQuantity("0");
    setThreshold("0");
    load();
  }

  async function updateThreshold(item: InventoryItem, newThreshold: string) {
    await api.patch(`/inventory/${item.id}`, { low_stock_threshold: Number(newThreshold) || 0 });
    load();
  }

  async function deleteItem(itemId: string) {
    await api.delete(`/inventory/${itemId}`);
    load();
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-800">Food Inventory</h1>
        <select
          value={locationFilter}
          onChange={(e) => setLocationFilter(e.target.value as InventoryLocation | "")}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm"
        >
          <option value="">All locations</option>
          {LOCATIONS.map((loc) => (
            <option key={loc.value} value={loc.value}>
              {loc.label}
            </option>
          ))}
        </select>
      </div>

      <form
        onSubmit={createItem}
        className="mb-6 flex flex-wrap items-end gap-2 rounded-lg bg-white p-4 shadow-sm"
      >
        <label className="text-xs text-slate-600">
          Name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Canned Tuna"
            className="mt-1 block rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-xs text-slate-600">
          Category
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as InventoryCategory)}
            className="mt-1 block rounded border border-slate-300 px-2 py-1.5 text-sm"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-slate-600">
          Location
          <select
            value={location}
            onChange={(e) => setLocation(e.target.value as InventoryLocation)}
            className="mt-1 block rounded border border-slate-300 px-2 py-1.5 text-sm"
          >
            {LOCATIONS.map((loc) => (
              <option key={loc.value} value={loc.value}>
                {loc.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-slate-600">
          Unit
          <input
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            placeholder="cans, lbs..."
            className="mt-1 block w-24 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-xs text-slate-600">
          Starting qty
          <input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="mt-1 block w-20 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-xs text-slate-600">
          Low-stock at
          <input
            type="number"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            className="mt-1 block w-20 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </label>
        <button type="submit" className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white">
          Add Item
        </button>
      </form>

      <table className="w-full overflow-hidden rounded-lg bg-white text-sm shadow-sm">
        <thead className="bg-slate-100 text-left text-xs uppercase text-slate-500">
          <tr>
            <th className="px-4 py-2">Item</th>
            <th className="px-4 py-2">Location</th>
            <th className="px-4 py-2">Category</th>
            <th className="px-4 py-2">Qty</th>
            <th className="px-4 py-2">Low-stock at</th>
            <th className="px-4 py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items?.map((item) => (
            <tr key={item.id} className={`border-t border-slate-100 ${item.is_low_stock ? "bg-red-50" : ""}`}>
              <td className="px-4 py-2 font-medium">{item.name}</td>
              <td className="px-4 py-2">{LOCATIONS.find((l) => l.value === item.location)?.label}</td>
              <td className="px-4 py-2 capitalize">{item.category.replace(/_/g, " ")}</td>
              <td className="px-4 py-2">
                {item.quantity} {item.unit}
                {item.is_low_stock && (
                  <span className="ml-2 rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-700">Low stock</span>
                )}
              </td>
              <td className="px-4 py-2">
                <input
                  type="number"
                  defaultValue={item.low_stock_threshold}
                  onBlur={(e) => updateThreshold(item, e.target.value)}
                  className="w-16 rounded border border-slate-300 px-1.5 py-1 text-xs"
                />
              </td>
              <td className="px-4 py-2 space-x-2 whitespace-nowrap">
                <button
                  onClick={() => adjust(item.id, 1)}
                  className="rounded bg-slate-200 px-2 py-1 text-xs hover:bg-slate-300"
                >
                  +1
                </button>
                <button
                  onClick={() => adjust(item.id, -1)}
                  className="rounded bg-slate-200 px-2 py-1 text-xs hover:bg-slate-300"
                >
                  -1
                </button>
                <button
                  onClick={() => deleteItem(item.id)}
                  className="rounded bg-red-100 px-2 py-1 text-xs text-red-700 hover:bg-red-200"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {items?.length === 0 && <p className="mt-4 text-slate-500">No items found.</p>}
    </div>
  );
}
