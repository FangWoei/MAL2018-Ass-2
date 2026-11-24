USE MAL2018_Profile;
GO

CREATE OR ALTER TRIGGER CW2.trg_UserProfile_AfterInsert
ON CW2.UserProfile
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO CW2.UserLog (UserID, Username, Email)
    SELECT i.UserID, i.Username, i.Email
    FROM inserted AS i;
END;
GO