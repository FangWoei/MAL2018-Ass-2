USE MAL2018_Profile;
GO

-- CREATE: only the username is required
CREATE OR ALTER PROCEDURE CW2.usp_CreateUserProfile
    @Username   NVARCHAR(50),
    @Email      NVARCHAR(254) = NULL,
    @FirstName  NVARCHAR(50)  = NULL,
    @LastName   NVARCHAR(50)  = NULL,
    @NewUserID  INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @Username IS NULL OR LTRIM(RTRIM(@Username)) = N''
            THROW 50001, 'Username is required.', 1;

        INSERT INTO CW2.UserProfile (Username, Email, FirstName, LastName)
        VALUES (LTRIM(RTRIM(@Username)), @Email, @FirstName, @LastName);

        SET @NewUserID = SCOPE_IDENTITY();
    END TRY
    BEGIN CATCH
        IF ERROR_NUMBER() IN (2601, 2627)
            THROW 50002, 'Username or email already exists.', 1;
        THROW;
    END CATCH
END;
GO

-- READ: one member's full profile, from the view
CREATE OR ALTER PROCEDURE CW2.usp_GetUserProfile
    @UserID INT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM CW2.UserProfile WHERE UserID = @UserID)
        THROW 50003, 'User not found.', 1;

    SELECT * FROM CW2.vw_UserProfileDetails WHERE UserID = @UserID;
END;
GO

-- READ (login): find the profile that belongs to a verified email
CREATE OR ALTER PROCEDURE CW2.usp_GetUserByEmail
    @Email NVARCHAR(254)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT u.UserID, u.Username, r.RoleName
    FROM CW2.UserProfile AS u
    INNER JOIN CW2.Role AS r ON r.RoleID = u.RoleID
    WHERE u.Email = @Email;
END;
GO

-- READ (admin): list profiles, optionally filtered by part of a username
CREATE OR ALTER PROCEDURE CW2.usp_ListUserProfiles
    @Search NVARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT u.UserID, u.Username, u.Email, r.RoleName, u.DateJoined
    FROM CW2.UserProfile AS u
    INNER JOIN CW2.Role AS r ON r.RoleID = u.RoleID
    WHERE @Search IS NULL OR u.Username LIKE N'%' + @Search + N'%'
    ORDER BY u.Username;
END;
GO

-- UPDATE: only supplied values change (NULL = keep current value)
CREATE OR ALTER PROCEDURE CW2.usp_UpdateUserProfile
    @UserID                 INT,
    @Username               NVARCHAR(50)  = NULL,
    @Email                  NVARCHAR(254) = NULL,
    @FirstName              NVARCHAR(50)  = NULL,
    @LastName               NVARCHAR(50)  = NULL,
    @AboutMe                NVARCHAR(500) = NULL,
    @Location               NVARCHAR(100) = NULL,
    @HeightCm               SMALLINT      = NULL,
    @WeightKg               SMALLINT      = NULL,
    @UnitPreference         VARCHAR(10)   = NULL,
    @ActivityTimePreference VARCHAR(10)   = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        UPDATE CW2.UserProfile
        SET Username               = ISNULL(LTRIM(RTRIM(@Username)), Username),
            Email                  = ISNULL(@Email, Email),
            FirstName              = ISNULL(@FirstName, FirstName),
            LastName               = ISNULL(@LastName, LastName),
            AboutMe                = ISNULL(@AboutMe, AboutMe),
            Location               = ISNULL(@Location, Location),
            HeightCm               = ISNULL(@HeightCm, HeightCm),
            WeightKg               = ISNULL(@WeightKg, WeightKg),
            UnitPreference         = ISNULL(@UnitPreference, UnitPreference),
            ActivityTimePreference = ISNULL(@ActivityTimePreference, ActivityTimePreference)
        WHERE UserID = @UserID;

        IF @@ROWCOUNT = 0
            THROW 50003, 'User not found.', 1;
    END TRY
    BEGIN CATCH
        IF ERROR_NUMBER() IN (2601, 2627)
            THROW 50002, 'Username or email already exists.', 1;
        IF ERROR_NUMBER() = 547
            THROW 50004, 'A value is outside the allowed range or list.', 1;
        THROW;
    END CATCH
END;
GO

-- DELETE: ON DELETE CASCADE removes favourites and saved trails; UserLog rows are kept
CREATE OR ALTER PROCEDURE CW2.usp_DeleteUserProfile
    @UserID INT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM CW2.UserProfile WHERE UserID = @UserID)
        THROW 50003, 'User not found.', 1;

    DELETE FROM CW2.UserProfile WHERE UserID = @UserID;
END;
GO