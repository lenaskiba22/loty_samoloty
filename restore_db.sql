IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'AdventureWorks')
BEGIN
    RESTORE DATABASE AdventureWorks 
    FROM DISK = '/var/opt/mssql/backup/AdventureWorks.bak' 
    WITH MOVE 'AdventureWorks2014_Data' TO '/var/opt/mssql/data/AdventureWorks.mdf', 
         MOVE 'AdventureWorks2014_Log' TO '/var/opt/mssql/data/AdventureWorks.ldf';
END
GO

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'AWStaging')
BEGIN
    CREATE DATABASE AWStaging
END
GO

USE [AWStaging]
GO
CREATE SCHEMA raw
GO
CREATE SCHEMA stg
GO
CREATE SCHEMA dim
GO