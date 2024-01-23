﻿Select Name, Action, Compare, Location, Value, Performed, Avg (Result) as avg, Count (Result) as count
From (Select rowid, compareId, Performed, Result, Name, Action FROM (Select rowid, compareId, ActionId, Performed, Result FROM (Select p.rowid, f.compareId, p.Result From L_PlayRecord as p, L_FieldState as f Where f.HistoryId = p.rowid) as t2, L_ActionState as a where t2.rowid = a.HistoryId) as t3, L_ActionList as al WHERE t3.ActionId = al.rowid) as t4, L_CompareTo as ct
where compareId = ct.rowid and result != 0
Group By Name, Action, Compare, Location, Value, Performed
ORder By avg Desc, Name, Action, Compare, Location, Value