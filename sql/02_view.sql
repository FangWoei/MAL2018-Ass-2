USE MAL2018_Profile;
GO

CREATE OR ALTER VIEW CW2.vw_UserProfileDetails
AS
SELECT
    u.UserID, u.Username, u.Email, u.FirstName, u.LastName, u.AboutMe, u.Location,
    u.ProfilePictureURL, u.HeightCm, u.WeightKg, u.DateOfBirth, u.UnitPreference,
    u.ActivityTimePreference, r.RoleName, u.DateJoined,
    ISNULL(fa.FavouriteActivities, 'None') AS FavouriteActivities,
    ISNULL(st.SavedTrailCount, 0)          AS SavedTrailCount,
    ISNULL(st.SavedTrailIDs, 'None')       AS SavedTrailIDs
FROM CW2.UserProfile AS u
INNER JOIN CW2.Role AS r
    ON r.RoleID = u.RoleID
LEFT JOIN (
    SELECT ua.UserID,
           STRING_AGG(a.ActivityName, ', ') WITHIN GROUP (ORDER BY a.ActivityName) AS FavouriteActivities
    FROM CW2.UserActivity AS ua
    INNER JOIN CW2.Activity AS a ON a.ActivityID = ua.ActivityID
    GROUP BY ua.UserID
) AS fa ON fa.UserID = u.UserID
LEFT JOIN (
    SELECT UserID,
           COUNT(*) AS SavedTrailCount,
           STRING_AGG(CAST(TrailID AS VARCHAR(10)), ', ') WITHIN GROUP (ORDER BY TrailID) AS SavedTrailIDs
    FROM CW2.SavedTrail
    GROUP BY UserID
) AS st ON st.UserID = u.UserID;
GO