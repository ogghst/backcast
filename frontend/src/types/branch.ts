export interface Branch {
  name: string;
  type: "main" | "change_order";
  is_default: boolean;
  change_order_id?: string;
  change_order_code?: string;
  change_order_status?: string;
}
