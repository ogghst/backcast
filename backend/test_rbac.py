import asyncio

from app.core.rbac import get_rbac_service


async def main():
    rbac = get_rbac_service()
    print("Permissions for admin:", rbac.get_user_permissions("admin"))
    print(
        "Has override:", rbac.has_permission("admin", "change-order-override-approver")
    )


if __name__ == "__main__":
    asyncio.run(main())
