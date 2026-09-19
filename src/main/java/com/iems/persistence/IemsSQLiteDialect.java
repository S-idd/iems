package com.iems.persistence;

import java.sql.Types;
import org.hibernate.community.dialect.SQLiteDialect;

/** SQLite INTEGER PRIMARY KEY is a signed 64-bit rowid, including for Java Long IDs. */
public class IemsSQLiteDialect extends SQLiteDialect {
    @Override
    public boolean equivalentTypes(int first, int second) {
        return super.equivalentTypes(first, second)
                || (first == Types.INTEGER && second == Types.BIGINT)
                || (first == Types.BIGINT && second == Types.INTEGER);
    }
}
