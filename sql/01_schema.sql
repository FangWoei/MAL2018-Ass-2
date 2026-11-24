/* ============================================================
   01_schema.sql - ProfileService (CW2)
   Database, schema, tables, demo data. Safe to run repeatedly.
   ============================================================ */
IF DB_ID('MAL2018_Profile') IS NULL
    CREATE DATABASE MAL2018_Profile;
GO

USE MAL2018_Profile;
GO

IF SCHEMA_ID('CW2') IS NULL
    EXEC('CREATE SCHEMA CW2');
GO

IF OBJECT_ID('CW2.Role', 'U') IS NULL
CREATE TABLE CW2.Role (
    RoleID   INT IDENTITY(1,1) NOT NULL,
    RoleName VARCHAR(20)       NOT NULL,
    CONSTRAINT PK_Role          PRIMARY KEY (RoleID),
    CONSTRAINT UQ_Role_RoleName UNIQUE (RoleName)
);
GO

IF OBJECT_ID('CW2.Activity', 'U') IS NULL
CREATE TABLE CW2.Activity (
    ActivityID   INT IDENTITY(1,1) NOT NULL,
    ActivityName VARCHAR(50)       NOT NULL,
    CONSTRAINT PK_Activity              PRIMARY KEY (ActivityID),
    CONSTRAINT UQ_Activity_ActivityName UNIQUE (ActivityName)
);
GO

IF OBJECT_ID('CW2.UserProfile', 'U') IS NULL
CREATE TABLE CW2.UserProfile (
    UserID                 INT IDENTITY(1,1) NOT NULL,
    Username               NVARCHAR(50)      NOT NULL,
    Email                  NVARCHAR(254)     NULL,
    FirstName              NVARCHAR(50)      NULL,
    LastName               NVARCHAR(50)      NULL,
    AboutMe                NVARCHAR(500)     NULL,
    Location               NVARCHAR(100)     NULL,
    ProfilePictureURL      NVARCHAR(500)     NULL,
    HeightCm               SMALLINT          NULL,
    WeightKg               SMALLINT          NULL,
    DateOfBirth            DATE              NULL,
    UnitPreference         VARCHAR(10)       NULL CONSTRAINT DF_UserProfile_UnitPreference DEFAULT 'Metric',
    ActivityTimePreference VARCHAR(10)       NULL,
    RoleID                 INT               NOT NULL CONSTRAINT DF_UserProfile_RoleID DEFAULT 1,
    DateJoined             DATE              NOT NULL CONSTRAINT DF_UserProfile_DateJoined DEFAULT (CAST(GETDATE() AS DATE)),
    CONSTRAINT PK_UserProfile          PRIMARY KEY (UserID),
    CONSTRAINT UQ_UserProfile_Username UNIQUE (Username),
    CONSTRAINT FK_UserProfile_Role     FOREIGN KEY (RoleID) REFERENCES CW2.Role (RoleID),
    CONSTRAINT CK_UserProfile_Height   CHECK (HeightCm BETWEEN 100 AND 299),
    CONSTRAINT CK_UserProfile_Weight   CHECK (WeightKg BETWEEN 23 AND 407),
    CONSTRAINT CK_UserProfile_DOB      CHECK (DateOfBirth <= CAST(GETDATE() AS DATE)),
    CONSTRAINT CK_UserProfile_Units    CHECK (UnitPreference IN ('Metric', 'Imperial')),
    CONSTRAINT CK_UserProfile_TimePref CHECK (ActivityTimePreference IN ('Morning', 'Afternoon', 'Evening'))
);
GO

-- Emails must be unique when present (a plain UNIQUE would allow only one NULL)
IF NOT EXISTS (SELECT 1 FROM sys.indexes
               WHERE name = 'UX_UserProfile_Email'
                 AND object_id = OBJECT_ID('CW2.UserProfile'))
    CREATE UNIQUE INDEX UX_UserProfile_Email
        ON CW2.UserProfile (Email)
        WHERE Email IS NOT NULL;
GO

IF OBJECT_ID('CW2.UserActivity', 'U') IS NULL
CREATE TABLE CW2.UserActivity (
    UserID     INT NOT NULL,
    ActivityID INT NOT NULL,
    CONSTRAINT PK_UserActivity          PRIMARY KEY (UserID, ActivityID),
    CONSTRAINT FK_UserActivity_User     FOREIGN KEY (UserID)
        REFERENCES CW2.UserProfile (UserID) ON DELETE CASCADE,
    CONSTRAINT FK_UserActivity_Activity FOREIGN KEY (ActivityID)
        REFERENCES CW2.Activity (ActivityID)
);
GO

-- TrailID belongs to TrailService, so it has no foreign key
IF OBJECT_ID('CW2.SavedTrail', 'U') IS NULL
CREATE TABLE CW2.SavedTrail (
    UserID    INT  NOT NULL,
    TrailID   INT  NOT NULL,
    DateSaved DATE NOT NULL CONSTRAINT DF_SavedTrail_DateSaved DEFAULT (CAST(GETDATE() AS DATE)),
    CONSTRAINT PK_SavedTrail      PRIMARY KEY (UserID, TrailID),
    CONSTRAINT FK_SavedTrail_User FOREIGN KEY (UserID)
        REFERENCES CW2.UserProfile (UserID) ON DELETE CASCADE
);
GO

-- Audit log: no foreign key, so rows survive profile deletion
IF OBJECT_ID('CW2.UserLog', 'U') IS NULL
CREATE TABLE CW2.UserLog (
    LogID     INT IDENTITY(1,1) NOT NULL,
    UserID    INT               NOT NULL,
    Username  NVARCHAR(50)      NOT NULL,
    Email     NVARCHAR(254)     NULL,
    CreatedAt DATETIME2(0)      NOT NULL CONSTRAINT DF_UserLog_CreatedAt DEFAULT SYSDATETIME(),
    CONSTRAINT PK_UserLog PRIMARY KEY (LogID)
);
GO

/* ---------------- Demo data (only into an empty database) ---------------- */
IF NOT EXISTS (SELECT 1 FROM CW2.Role)
BEGIN
    INSERT INTO CW2.Role (RoleName) VALUES ('User'), ('Admin');

    INSERT INTO CW2.Activity (ActivityName) VALUES
        ('Hiking'), ('Running'), ('Mountain biking'), ('Road biking'),
        ('Camping'), ('Walking'), ('Birding');

    -- The three mandatory accounts (Grace = Admin is an assumption)
    INSERT INTO CW2.UserProfile
        (Username, Email, FirstName, LastName, AboutMe, Location, HeightCm, WeightKg,
         DateOfBirth, UnitPreference, ActivityTimePreference, RoleID)
    VALUES
        ('Grace Hopper', 'grace@plymouth.ac.uk', 'Grace', 'Hopper',
         'Admin account for the Trail App.', 'Plymouth, UK', 165, 60,
         '1990-05-14', 'Metric', 'Morning', 2),
        ('Tim Berners-Lee', 'tim@plymouth.ac.uk', 'Tim', 'Berners-Lee',
         'Weekend hiker who loves coastal paths.', 'London, UK', 180, 75,
         '1988-08-02', 'Metric', 'Afternoon', 1),
        ('Ada Lovelace', 'ada@plymouth.ac.uk', 'Ada', 'Lovelace',
         'Trail runner and birdwatcher.', 'Bristol, UK', 170, 62,
         '1995-12-10', 'Imperial', 'Evening', 1);

    -- A fourth user created with only a username
    INSERT INTO CW2.UserProfile (Username) VALUES ('TrailWalker');

    INSERT INTO CW2.UserActivity (UserID, ActivityID)
    SELECT u.UserID, a.ActivityID
    FROM (VALUES ('Grace Hopper', 'Hiking'),    ('Grace Hopper', 'Running'),
                 ('Tim Berners-Lee', 'Hiking'), ('Tim Berners-Lee', 'Camping'),
                 ('Ada Lovelace', 'Walking'),   ('Ada Lovelace', 'Birding'))
         AS v (Username, ActivityName)
    JOIN CW2.UserProfile AS u ON u.Username = v.Username
    JOIN CW2.Activity    AS a ON a.ActivityName = v.ActivityName;

    INSERT INTO CW2.SavedTrail (UserID, TrailID, DateSaved)
    SELECT u.UserID, v.TrailID, v.DateSaved
    FROM (VALUES ('Grace Hopper', 101, '2026-09-20'),
                 ('Grace Hopper', 102, '2026-09-25'),
                 ('Tim Berners-Lee', 101, '2026-10-01'),
                 ('Ada Lovelace', 205, '2026-10-05'))
         AS v (Username, TrailID, DateSaved)
    JOIN CW2.UserProfile AS u ON u.Username = v.Username;

    -- The trigger is created later, so seed the log from the existing users
    INSERT INTO CW2.UserLog (UserID, Username, Email)
    SELECT UserID, Username, Email FROM CW2.UserProfile;
END
GO