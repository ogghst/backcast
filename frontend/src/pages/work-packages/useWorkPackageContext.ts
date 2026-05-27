import { useOutletContext } from "react-router-dom";
import type { WorkPackageRead } from "@/api/generated";

export function useWorkPackageContext() {
  return useOutletContext<{ workPackage: WorkPackageRead }>();
}
