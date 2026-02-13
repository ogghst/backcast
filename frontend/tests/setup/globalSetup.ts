import { Client } from "pg";
import * as dotenv from "dotenv";
import * as path from "path";
import { fileURLToPath } from "url";

// ES module compatibility: get __dirname equivalent
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Playwright global setup hook.
 * Resets the test database before the entire test suite runs.
 *
 * This ensures test isolation by truncating all tables and resetting
 * auto-increment sequences before each test suite execution.
 *
 * Pattern matches backend/tests/conftest.py cleanup strategy.
 */
async function globalSetup() {
  console.log("🧹 Resetting test database...");

  // Load environment variables from project root
  const envPath = path.resolve(__dirname, "../../../.env");
  dotenv.config({ path: envPath });

  // Validate required environment variables
  const requiredVars = [
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_SERVER",
    "POSTGRES_PORT",
    "POSTGRES_DB",
  ];
  const missingVars = requiredVars.filter((varName) => !process.env[varName]);

  if (missingVars.length > 0) {
    throw new Error(
      `Missing required environment variables: ${missingVars.join(", ")}\n` +
        `Please ensure .env file exists at: ${envPath}`
    );
  }

  // Build connection string from environment variables
  const connectionString = `postgresql://${process.env.POSTGRES_USER}:${process.env.POSTGRES_PASSWORD}@${process.env.POSTGRES_SERVER}:${process.env.POSTGRES_PORT}/${process.env.POSTGRES_DB}`;

  console.log(
    `📡 Connecting to database: ${process.env.POSTGRES_SERVER}:${process.env.POSTGRES_PORT}/${process.env.POSTGRES_DB}`
  );

  const client = new Client({
    connectionString,
    connectionTimeoutMillis: 5000, // 5 second timeout
  });

  try {
    // Connect to database
    await client.connect();
    console.log("✅ Connected to test database");

    // Truncate all tables with CASCADE to handle foreign keys
    // RESTART IDENTITY resets auto-increment counters
    // Order doesn't matter due to CASCADE, but listed for clarity
    const startTime = Date.now();

    await client.query(`
      TRUNCATE TABLE 
        cost_elements, 
        cost_element_types, 
        wbes, 
        projects, 
        departments, 
        users 
      RESTART IDENTITY CASCADE
    `);

    const duration = Date.now() - startTime;
    console.log(`✅ Test database reset complete (${duration}ms)`);
    console.log(
      "📊 All tables truncated: cost_elements, cost_element_types, wbes, projects, departments, users"
    );

    // 2. Re-seed database
    console.log("🌱 Re-seeding database...");
    const { execSync } = await import("child_process");
    const scriptPath = path.resolve(__dirname, "../../../scripts/reseed.py");
    execSync(`python3 "${scriptPath}"`, { stdio: "inherit" });
    console.log("✅ Database re-seeded successfully");
  } catch (error) {
    console.error("❌ Database reset failed:", error);

    // Provide helpful error messages based on error type
    if (error instanceof Error) {
      if (error.message.includes("ECONNREFUSED")) {
        throw new Error(
          `Failed to connect to database. Please ensure PostgreSQL is running on ${process.env.POSTGRES_SERVER}:${process.env.POSTGRES_PORT}\n` +
            `Original error: ${error.message}`
        );
      } else if (error.message.includes("password authentication failed")) {
        throw new Error(
          `Database authentication failed. Please check POSTGRES_USER and POSTGRES_PASSWORD in .env file.\n` +
            `Original error: ${error.message}`
        );
      } else if (error.message.includes("does not exist")) {
        throw new Error(
          `Database or table does not exist. This may be expected on first run.\n` +
            `Original error: ${error.message}`
        );
      }
    }

    throw new Error(
      `Failed to reset test database. Please check your database connection and credentials.\n${error}`
    );
  } finally {
    // Always close the connection
    await client.end();
    console.log("🔌 Database connection closed");
  }
}

export default globalSetup;
