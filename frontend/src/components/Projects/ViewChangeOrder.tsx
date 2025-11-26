import { Button } from "@chakra-ui/react"
import { useState } from "react"
import { FaEye } from "react-icons/fa"
import type { ChangeOrderPublic } from "@/client"
import {
  DialogActionTrigger,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog"
import ChangeOrderDetailView from "./ChangeOrderDetailView"

interface ViewChangeOrderProps {
  changeOrder: ChangeOrderPublic
}

const ViewChangeOrder = ({ changeOrder }: ViewChangeOrderProps) => {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <DialogRoot
      size={{ base: "xs", md: "xl" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          aria-label="View change order"
          title="View change order"
        >
          <FaEye fontSize="16px" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change Order Details</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <ChangeOrderDetailView
            changeOrderId={changeOrder.change_order_id}
            projectId={changeOrder.project_id}
          />
        </DialogBody>
        <DialogFooter gap={2}>
          <DialogActionTrigger asChild>
            <Button variant="subtle" colorPalette="gray">
              Close
            </Button>
          </DialogActionTrigger>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

export default ViewChangeOrder
