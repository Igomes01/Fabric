# 📅 Interactive Absence Dashboard with Microsoft Fabric + Power BI

> How Microsoft Brazil is using Fabric for data application development.

## About the Project

This repository demonstrates how to use **User Data Functions** from Microsoft Fabric integrated with **Power BI** to create an interactive calendar dashboard for managing team absences.

![Dashboard navigation demo](images/navigation.gif)

---

## Prerequisites

| Requirement | Documentation |
|-------------|---------------|
| Active Fabric capacity | [How to purchase](https://learn.microsoft.com/en-us/fabric/enterprise/buy-subscription) |
| Workspace created and linked to the capacity | [Create workspaces](https://learn.microsoft.com/en-us/fabric/fundamentals/create-workspaces) |

---

## Table of Contents

1. [Create the Warehouse](#step-1---create-the-warehouse)
2. [Create User Data Functions](#step-2---create-user-data-functions-udf)
3. [Test the Functions](#step-3---test-the-functions)
4. [Publish the Function](#step-4---publish-the-function)
5. [Connect data sources to Power BI](#step-5---connect-data-sources-to-power-bi)
6. [Connect Function to Power BI](#step-6---connect-user-data-function-to-power-bi)
7. [Data Model](#step-7---data-model)
8. [Publish the Dashboard](#step-8---publish-the-dashboard)
9. [Refresh Import data via Pipeline](#step-9---refresh-import-data-via-pipeline)

---

## Step 1 - Create the Warehouse

The Warehouse is required to host the Power BI data and will also be used as the location where Fabric functions connect to modify data.

To create the Warehouse, inside the Fabric workspace:

> **Fabric Workspace** → **New Item** → **Warehouse**

Once the database is created, you need to create 3 tables:
- A table with employee information
- A fact table for absence records
- A dimension table to summarize absence types

### Step 1.1 - Create the Tables

Inside the Warehouse, click **New SQL Query** and run the queries below:

![New SQL query in Warehouse](images/warehouse_sql_query.png)

```sql
CREATE TABLE STAFFs (
    domainname VARCHAR(255),
    firstname VARCHAR(255),
    fullname VARCHAR(255),
    managername VARCHAR(255),
    title VARCHAR(255)
);

CREATE TABLE fOoO (
    Id VARCHAR(32) NOT NULL,
    Employee VARCHAR(255) NOT NULL,
    Type VARCHAR(255) NOT NULL,
    StartDate DATE NOT NULL,
    EndDate DATE NOT NULL
);

CREATE TABLE dim_OoO (
    Type VARCHAR(255) NOT NULL,
    Id INT
);

-- Insert dimension data
INSERT INTO dim_OoO (Type, Id) VALUES
('Vacation', 1),
('HHTO', 2),
('License', 3),
('OoO', 4);
```

---

## Step 2 - Create User Data Functions (UDF)

User Data Functions are reusable Python functions that can be invoked across Microsoft Fabric and external applications. They provide a serverless compute environment to host and execute code directly in Fabric.

📖 [Official UDF documentation](https://learn.microsoft.com/en-us/fabric/data-engineering/user-data-functions/user-data-functions-overview)
📄 [Documented function code](Codes/data_function_en-us.py)

**1.** Inside the Fabric Workspace, create a new UDF:

> **Workspace** → **New Item** → **User Data Function** → Enter Name

📖 [How to create UDF in the portal](https://learn.microsoft.com/en-us/fabric/data-engineering/user-data-functions/create-user-data-functions-portal)

**2.** Once the function is created, click **New Function** and then click **Configure Connections**:

![User Data Function home screen](images/user_data_function_home.png)

**3.** In Configure Connections, add the connection to the Warehouse created earlier:

> **Configure Connections** → **Add Connection** → Select the Warehouse

Select the created connection and click the pencil icon to edit it:

![Edit connection](images/edit_connection.png)

In the **Alias** field, replace the value with `MyWarehouse` and click **Update**:

![MyWarehouse alias configuration](images/my_warehouse.png)

Close the connections panel.

**4.** Replace the default code with the code below:

> ⚠️ In the `warehouse_name` field, enter your database name.

```python
import fabric.functions as fn
import re
import time
import random

udf = fn.UserDataFunctions()

# Enter your database name
warehouse_name = ""


def uuid_v7():
    """Generates a unique timestamp-based ID for each operation."""
    timestamp_ms = int(time.time() * 1000)
    rand_bits = random.getrandbits(74)

    return (
        f"{timestamp_ms:012x}"
        f"{rand_bits:018x}"
    )


@udf.connection(argName="myWarehouse", alias="MyWarehouse")
@udf.function()
def inserte_OoO(myWarehouse: fn.FabricSqlConnection, employee: str, ftype: str, startdate: str, enddate: str) -> str:
    """Inserts an absence record into the Warehouse."""

    id_gerado = uuid_v7()
    connection = myWarehouse.connect()
    cursor = connection.cursor()
    cursor.execute(f"USE [{warehouse_name}]")
    message = ""

    try:
        query = f"INSERT INTO [{warehouse_name}].[dbo].[fOoO] (Id, Employee, Type, StartDate, EndDate) VALUES (?, ?, ?, ?, ?)"
        cursor.execute(query, id_gerado, employee, ftype, startdate, enddate)
        message = "OoO Inserted"
    except Exception as e:
        message = f"Error processing: {e}"

    connection.commit()
    cursor.close()
    connection.close()

    return message


@udf.connection(argName="myWarehouse", alias="MyWarehouse")
@udf.function()
def delete_OoO(myWarehouse: fn.FabricSqlConnection, employee: str, dateids: str) -> str:
    """Removes absence records from the Warehouse."""

    itens = re.findall(r"'(.*?)'", dateids)
    connection = myWarehouse.connect()
    cursor = connection.cursor()
    cursor.execute(f"USE [{warehouse_name}]")
    message = ""

    for i in itens:
        try:
            query = f"DELETE FROM [{warehouse_name}].[dbo].[fOoO] WHERE Employee = ? AND Id = ?"
            cursor.execute(query, employee, i)
            message = "OoO Deleted"
        except Exception as e:
            message = f"Error processing: {e}"
            continue

    connection.commit()
    cursor.close()
    connection.close()

    return message
```

---

## Step 3 - Test the Functions

**1.** In the right sidebar, under the **Function Explorer**, select the `inserte_OoO` function and click the test icon:

![Function Explorer](images/test_functions.png)

**2.** Enter test values:

![Test with sample values](images/test_functions2.png)

| Parameter | Example Value |
|-----------|--------------|
| `employee` | Employee1 |
| `ftype` | OoO |
| `startdate` | 2026-01-01 |
| `enddate` | 2026-01-02 |

**3.** Click **Test** and wait for execution.

**4.** After a successful result, go back to the Warehouse and run the query below to confirm the insertion:

```sql
SELECT * FROM fOoO;
```

![Test result in Warehouse](images/results_test_1.png)

---

## Step 4 - Publish the Function

Inside the User Data Function, click **Publish** to make it available as an application:

![Publish function](images/publish_function.png)

---

## Step 5 - Connect data sources to Power BI

**1.** Go back to the Warehouse and click the gear icon to get the **SQL connection string**:

![SQL connection string](images/string_sql.png)

**2.** In Power BI Desktop, open the [`OoO_Dash.pbix`](pbi_file/OoO_Dash.pbix) file and go to **Transform Data**.

**3.** Paste the SQL string into the `warehouse_endpoint` parameter and enter the database name in `warehouse_name`:

![Power Query configuration](images/power_query.png)

**4.** Click **Close & Apply** and refresh the semantic model.

---

## Step 6 - Connect User Data Function to Power BI

### 6.1 - Save Data

On the dashboard home page, select the **"Save OoO"** button and go to the **Actions** tab:

![Save OoO button](images/save_Ooo_1.png)

In the Actions tab, under **Type**, select **Data Function**. Click the **fx** icon to select the `inserte_OoO` function and click **Connect**:

![Save action configuration](images/save_Ooo_2.png)

Fill in the fields as follows:

| Field | Configuration |
|-------|---------------|
| `Employee` | Click **fx** → select the `Connected User` measure |
| `ftype` | Click the options bar → select `Type` + enable **Auto Clear** |
| `startdate` | Click **fx** → select the `Start Date` measure |
| `enddate` | Click **fx** → select the `End Date` measure |

With the fields filled in, select a date, an absence type, and click **Save**. The data will appear in the Gantt chart on the dashboard.

### 6.2 - Delete Data

Select the **"Remove OoO"** item and go to **Actions**. Select the Data Function `delete_OoO`:

![Delete action configuration](images/save_Ooo_3.png)

Fill in the fields:

| Field | Configuration |
|-------|---------------|
| `employee` | Click **fx** → select the `Connected User` measure |
| `dateids` | Click **fx** → select the `Delete Date` measure |

Now you can click anywhere on the calendar chart, select a date, and click **Remove OoO** to delete the data from the database.

**Final result:**

![Dashboard navigation demo](images/navigation.gif)

---

## Step 7 - Data Model

In the **Model View** tab in Power BI, you will find the connected tables in a mixed storage format:

- **4 tables in Import** (dimensions)
- **1 table in Direct Query** (fact table — blue line on top)

![Data model view](images/model_view.png)

The fact table `fOoO` is in **Direct Query** because it constantly receives new data, requiring a real-time connection.

The remaining tables (dimensions) can stay in **Import** since they don't receive data frequently.

> ⚠️ **IMPORTANT:** Tables in Import format should be configured to **not refresh** along with the semantic model. Otherwise, every function execution will force an unnecessary refresh of these tables.

![Refresh configuration in Power Query](images/power_query_2.png)

### Row Level Security (RLS)

The dashboard has **RLS (Row Level Security)** that allows each user to view only the data linked to their manager, based on the `STAFFs` table.

To view the RLS:

> **Modeling** → **Manage Roles**

---

## Step 8 - Publish the Dashboard

Click **Publish** and select the workspace that will host the Power BI report.

To share the dashboard with other users, configure the following permissions:

| Resource | Required Permission |
|----------|---------------------|
| Power BI Report | Share with users |
| Semantic Model | Read access to the model |
| Warehouse | Read access |
| User Data Function | Read and execute access |

---

## Step 9 - Refresh Import data via Pipeline

Since we disabled the automatic refresh for Import tables (Step 7), you need to create a **Fabric Pipeline** to update them manually whenever there are changes to dimension data.

**1.** In the workspace, create a new Pipeline:

> **Workspace** → **New Item** → **Data Pipeline**

**2.** Inside the Pipeline, in the top toolbar, go to **Activities** and select **"Semantic model refresh"**:

![Add semantic model to pipeline](images/pipeline1.png)

**3.** Click the added item and go to **Settings** → **Connection**. Authenticate with your user account:

![Pipeline connection with user](images/pipeline2.png)

**4.** Below Connection, select the **Workspace** where the semantic model was published. Then, select the **Power BI report** published earlier.

**5.** In **Tables**, select only the tables that are in **Import** format:

![Select tables for pipeline refresh](images/pipeline3.png)

**6.** Click **Save** and run the Pipeline whenever you need to refresh the Import tables.

> 💡 **Tip:** You can also schedule the Pipeline to run automatically at regular intervals.

---

## References

- [User Data Functions overview](https://learn.microsoft.com/en-us/fabric/data-engineering/user-data-functions/user-data-functions-overview)
- [Create User Data Functions in the portal](https://learn.microsoft.com/en-us/fabric/data-engineering/user-data-functions/create-user-data-functions-portal)
- [Purchase Fabric capacity](https://learn.microsoft.com/en-us/fabric/enterprise/buy-subscription)
- [Create workspaces in Fabric](https://learn.microsoft.com/en-us/fabric/fundamentals/create-workspaces)
