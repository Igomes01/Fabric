"""
AIC - User Data Function (UDF) for absence management in Microsoft Fabric.

This module implements two main functions that connect to a Fabric Warehouse
to insert and delete absence (Out of Office - OoO) records for employees.

The functions are exposed as reusable endpoints via the fabric.functions framework,
and can be invoked by Power BI or external applications.

Dependencies:
    - fabric.functions: Fabric SDK for creating User Data Functions
    - re: Regular expressions for ID parsing
    - time: Timestamp generation for unique IDs
    - random: Random bit generation for unique IDs
"""

import fabric.functions as fn
import re
import time
import random

# AIC - Initializes the main User Data Functions framework object.
# This object is responsible for registering and managing all exposed functions.
udf = fn.UserDataFunctions()

# AIC - Database (Warehouse) name in Fabric.
# Must be filled with the exact name of the Warehouse created in Step 1.
# Example: warehouse_name = "MyWarehouse"
warehouse_name = ""


def uuid_v7():
    """
    AIC - Generates a unique timestamp-based identifier (inspired by UUID v7).

    The ID is composed of:
        - 12 hexadecimal characters from the millisecond timestamp (ensures temporal ordering)
        - 18 hexadecimal characters from random bits (ensures uniqueness)

    Returns:
        str: Unique 30-character hexadecimal ID.

    Example return: "018f6b1a2c3d00a1b2c3d4e5f6a7b8"
    """
    # AIC - Captures the current timestamp in milliseconds since epoch (01/01/1970)
    timestamp_ms = int(time.time() * 1000)

    # AIC - Generates 74 random bits to compose the unique portion of the ID
    rand_bits = random.getrandbits(74)

    # AIC - Concatenates timestamp (12 hex) + random bits (18 hex) forming the final ID
    return (
        f"{timestamp_ms:012x}"
        f"{rand_bits:018x}"
    )


@udf.connection(argName="myWarehouse", alias="MyWarehouse")
@udf.function()
def inserte_OoO(myWarehouse: fn.FabricSqlConnection, employee: str, ftype: str, startdate: str, enddate: str) -> str:
    """
    AIC - Inserts a new absence (OoO) record into the fOoO table in the Warehouse.

    This function is invoked by the "Save OoO" button in Power BI.

    Decorators:
        @udf.connection: Injects the Warehouse connection using the "MyWarehouse" alias
                         configured in the UDF Configure Connections step.
        @udf.function: Registers this function as an invocable endpoint.

    Parameters:
        myWarehouse (FabricSqlConnection): Connection automatically injected by Fabric.
        employee (str): Employee name/identifier (comes from the "Connected User" measure in PBI).
        ftype (str): Absence type (e.g.: "Vacation", "OoO", "HHTO", "License").
        startdate (str): Absence start date (format: YYYY-MM-DD).
        enddate (str): Absence end date (format: YYYY-MM-DD).

    Returns:
        str: Success message ("OoO Inserted") or error message.
    """

    # AIC - Generates a unique ID for the new absence record
    id_gerado = uuid_v7()

    # AIC - Establishes connection to the Warehouse via the object injected by the decorator
    connection = myWarehouse.connect()
    cursor = connection.cursor()

    # AIC - Selects the correct database for query execution
    cursor.execute(f"USE [{warehouse_name}]")
    message = ""

    try:
        # AIC - Inserts the record into the fOoO table using positional parameters (?)
        # to prevent SQL Injection
        query = f"INSERT INTO [{warehouse_name}].[dbo].[fOoO] (Id, Employee, Type, StartDate, EndDate) VALUES (?, ?, ?, ?, ?)"
        cursor.execute(query, id_gerado, employee, ftype, startdate, enddate)
        message = "OoO Inserted"
    except Exception as e:
        message = f"Error processing: {e}"

    # AIC - Commits the transaction and releases connection resources
    connection.commit()
    cursor.close()
    connection.close()

    return message


@udf.connection(argName="myWarehouse", alias="MyWarehouse")
@udf.function()
def delete_OoO(myWarehouse: fn.FabricSqlConnection, employee: str, dateids: str) -> str:
    """
    AIC - Removes absence (OoO) records from the fOoO table in the Warehouse.

    This function is invoked by the "Remove OoO" button in Power BI.
    Supports removing multiple records at once by receiving IDs
    in a single-quoted string format.

    Decorators:
        @udf.connection: Injects the Warehouse connection using the "MyWarehouse" alias.
        @udf.function: Registers this function as an invocable endpoint.

    Parameters:
        myWarehouse (FabricSqlConnection): Connection automatically injected by Fabric.
        employee (str): Employee name/identifier (comes from the "Connected User" measure in PBI).
        dateids (str): String containing IDs enclosed in single quotes for removal.
                       Expected format: "'id1','id2','id3'"
                       (comes from the "Delete Date" measure in PBI).

    Returns:
        str: Success message ("OoO Deleted") or error message from the last processed item.
    """

    # AIC - Extracts all IDs from the string using regex.
    # The pattern r"'(.*?)'" captures content between single quotes.
    # Example: "'abc123','def456'" → ['abc123', 'def456']
    itens = re.findall(r"'(.*?)'", dateids)

    # AIC - Establishes connection to the Warehouse
    connection = myWarehouse.connect()
    cursor = connection.cursor()
    cursor.execute(f"USE [{warehouse_name}]")
    message = ""

    # AIC - Iterates over each ID to delete individually
    for i in itens:
        try:
            # AIC - Deletes the record using Employee + Id as a composite key
            # to ensure a user can only delete their own records
            query = f"DELETE FROM [{warehouse_name}].[dbo].[fOoO] WHERE Employee = ? AND Id = ?"
            cursor.execute(query, employee, i)
            message = "OoO Deleted"
        except Exception as e:
            message = f"Error processing: {e}"
            # AIC - On error, skips to the next item without interrupting the loop
            continue

    # AIC - Commits all deletions in a single transaction and releases resources
    connection.commit()
    cursor.close()
    connection.close()

    return message
