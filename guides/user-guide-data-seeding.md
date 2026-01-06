# User Guide: Data Seeding System

## Overview

The Backcast EVS backend includes an automatic data seeding system that initializes the database with essential data on startup. This ensures a consistent baseline configuration across all environments (development, testing, production).

## Features

### Automatic Seeding

The seeding system runs automatically every time the backend starts. It:

- ✅ Creates a default admin user if not present
- ✅ Initializes default departments
- ✅ Is **idempotent** - safe to run multiple times without creating duplicates
- ✅ Uses Pydantic validation to ensure data integrity
- ✅ Logs detailed information about what was seeded

### Default Admin User

**Credentials**:

- **Email**: `admin@backcast.local`
- **Password**: `ChangeMe123!`
- **Role**: `admin`

> [!CAUTION] > **SECURITY REQUIREMENT**: You MUST change the default admin password immediately after first login!
>
> The default password is stored in the codebase for development convenience. For production deployments:
>
> 1. Login with the default credentials
> 2. Navigate to user profile settings
> 3. Change the password to a strong, unique password
> 4. Consider implementing a password rotation policy

### Password Change Tracking

The system tracks when passwords were last changed using the `password_changed_at` field. This enables:

- Password age monitoring
- Password expiry policies
- Security audits

When a user is created through seeding, this field is `null`, indicating the password has never been changed.

## Configuration

### Seed Data Location

Seed data is stored in JSON files located at:

```
backend/seed/
├── users.json        # User accounts
└── departments.json  # Organizational departments
```

### Adding Seed Data

To add new seed data:

1. **Create or modify JSON files** in `backend/seed/`

2. **Follow the schema format**:

   **Users (`users.json`)**:

   ```json
   [
     {
       "email": "user@example.com",
       "password": "SecurePassword123!",
       "full_name": "John Doe",
       "role": "viewer",
       "department": null
     }
   ]
   ```

   **Departments (`departments.json`)**:

   ```json
   [
     {
       "code": "DEPT-CODE",
       "name": "Department Name",
       "manager_id": null,
       "is_active": true
     }
   ]
   ```

3. **Restart the backend** - seeding runs automatically on startup

### Idempotency

The seeding system checks for existing entities before creating new ones:

- **Users**: Checked by `email` address
- **Departments**: Checked by `code`

If an entity already exists, it will be skipped with a log message:

```
INFO - User admin@backcast.local already exists, skipping
INFO - User seeding complete: 0 created, 1 skipped
```

## Usage

### Development Workflow

1. **First Startup**: Default admin user is created automatically
2. **Login**: Use `admin@backcast.local` / `ChangeMe123!`
3. **Change Password**: Update admin password in user settings
4. **Add Users**: Create additional users via the UI or API
5. **Subsequent Restarts**: Seeding skips existing users (idempotent)

### Production Deployment

For production environments, follow these steps:

1. **Deploy the application** with seed files included
2. **First startup** creates the admin user
3. **Immediate action required**:
   - Login with default credentials
   - Change the admin password
   - Create additional admin users if needed
   - Consider removing or restricting the default admin account
4. **Verify seeding logs** to confirm successful initialization

### Environment-Specific Seeding

To use different seed data for different environments:

1. **Option A**: Maintain separate seed files

   ```
   seed/
   ├── users.development.json
   ├── users.production.json
   └── departments.json
   ```

   Copy the appropriate file to `users.json` during deployment

2. **Option B**: Use environment variables (future enhancement)
   ```bash
   ADMIN_EMAIL=admin@company.com
   ADMIN_PASSWORD=<secure-password>
   ```

## Troubleshooting

### Seeding Not Running

**Symptom**: Admin user not created on startup

**Diagnosis**:

1. Check application logs for seeding messages:

   ```
   INFO - === Starting database seeding ===
   INFO - Starting department seeding...
   INFO - Starting user seeding...
   INFO - === Database seeding completed successfully ===
   ```

2. If logs are missing, check that `main.py` includes the seeder

**Resolution**:

- Verify seed files exist in `backend/seed/`
- Check file permissions (must be readable)
- Ensure JSON is valid (use a JSON validator)

### Duplicate Users Not Being Skipped

**Symptom**: Error about duplicate email on restart

**Diagnosis**:

- Check database for existing users with same email
- Verify seeder is checking email before creation

**Resolution**:

- This should not happen with the current implementation
- If it does, it indicates a bug - please report it

### Invalid Seed Data

**Symptom**: Seeding logs show validation errors

**Example**:

```
ERROR - Failed to seed user at index 0: validation error for UserRegister
```

**Diagnosis**:

- Pydantic schema validation failed
- Check JSON data matches required format

**Resolution**:

1. Validate JSON syntax (commas, brackets, quotes)
2. Ensure all required fields are present:
   - Users: `email`, `password`, `full_name`, `role`
   - Departments: `code`, `name`, `is_active`
3. Check field types match schema (strings, booleans, etc.)
4. Verify email format is valid
5. Ensure password meets minimum length (8 characters)

## Security Best Practices

### Password Management

1. **Never commit production passwords** to version control
2. **Change default passwords immediately** after deployment
3. **Use strong passwords**: minimum 12 characters, mixed case, numbers, symbols
4. **Implement password rotation**: Change passwords regularly
5. **Monitor password age**: Use `password_changed_at` field to track this

### Access Control

1. **Limit admin accounts**: Create only necessary admin users
2. **Use role-based access**: Assign appropriate roles (admin, editor, viewer)
3. **Audit access**: Monitor who logs in with admin credentials
4. **Revoke unused accounts**: Disable or delete accounts that are no longer needed

### Production Hardening

For production deployments, consider:

1. **Remove seed files** after initial deployment
2. **Use environment variables** for sensitive data (future feature)
3. **Implement forced password change** on first login (future feature)
4. **Enable audit logging** for admin actions
5. **Set up monitoring** for failed login attempts

## Extending the Seeder

To add seeding for new entity types:

1. **Create a seed file**: `backend/seed/entity_name.json`

2. **Add a seeding method** to `DataSeeder` class:

   ```python
   async def seed_entities(self, session: AsyncSession) -> None:
       """Seed entities from entity_name.json file."""
       from app.services.entity import EntityService

       logger.info("Starting entity seeding...")
       entity_data = self.load_seed_file("entity_name.json")

       if not entity_data:
           logger.info("No entity seed data found")
           return

       entity_service = EntityService(session)
       created_count = 0
       skipped_count = 0

       for idx, entity_dict in enumerate(entity_data):
           try:
               entity_in = EntityCreate(**entity_dict)

               # Check if exists (adjust field name as needed)
               existing = await entity_service.get_by_field(entity_in.field)
               if existing:
                   logger.debug(f"Entity {entity_in.field} exists, skipping")
                   skipped_count += 1
                   continue

               await entity_service.create_entity(entity_in, uuid4())
               created_count += 1
               logger.info(f"Created entity: {entity_in.field}")
           except Exception as e:
               logger.error(f"Failed to seed entity at index {idx}: {e}")
               continue

       logger.info(f"Entity seeding complete: {created_count} created, {skipped_count} skipped")
   ```

3. **Update `seed_all` method** to include new entity type:

   ```python
   async def seed_all(self, session: AsyncSession) -> None:
       """Execute all seeding operations."""
       logger.info("=== Starting database seeding ===")

       try:
           await self.seed_departments(session)
           await self.seed_entities(session)  # Add new seeder
           await self.seed_users(session)

           await session.commit()
           logger.info("=== Database seeding completed successfully ===")
       except Exception as e:
           logger.error(f"Database seeding failed: {e}")
           await session.rollback()
           raise
   ```

4. **Add tests** for the new seeding method in `tests/unit/db/test_seeder.py`

## Related Documentation

- **[Architecture: Data Seeding](file:///home/nicola/dev/backcast_evs/docs/02-architecture/)** - Technical architecture details
- **[Implementation Walkthrough](file:///home/nicola/.gemini/antigravity/brain/8d1b033e-4dd1-4518-aa46-19c4f409bfb5/walkthrough.md)** - Development process and decisions
- **[User Management API](file:///home/nicola/dev/backcast_evs/backend/app/api/routes/users.py)** - API endpoints for user operations

## Support

If you encounter issues with data seeding:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review application logs for error messages
3. Verify seed file format matches schema requirements
4. Report bugs with:
   - Seed file contents (sanitize passwords!)
   - Application logs
   - Database state
   - Expected vs. actual behavior
