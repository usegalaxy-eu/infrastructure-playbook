environments {
    production {
        dataSource{
            dbCreate = "update" // one of 'create', 'create-drop', 'update', 'validate', ''
            username = "{{ apollo_db_username }}"
            password = "{{ apollo_db_password }}"
            driverClassName = "org.postgresql.Driver"
            dialect = org.hibernate.dialect.PostgresPlusDialect
            url = "{{ apollo_db_uri }}"
            properties {
                // See http://grails.org/doc/latest/guide/conf.html#dataSource for documentation
                jmxEnabled = true
                initialSize = 5
                maxActive = 50
                minIdle = 5
                maxIdle = 25
                maxWait = 10000
                maxAge = 10 * 60000
                timeBetweenEvictionRunsMillis = 5000
                minEvictableIdleTimeMillis = 60000
                validationQuery = "SELECT 1"
                validationQueryTimeout = 3
                validationInterval = 15000
                testOnBorrow = true
                testWhileIdle = true
                testOnReturn = false
                jdbcInterceptors = "ConnectionState"
                defaultTransactionIsolation = java.sql.Connection.TRANSACTION_READ_COMMITTED
            }
        }
        dataSource_chado{
            dbCreate = "update" // one of 'create', 'create-drop', 'update', 'validate', ''
            username = "{{ apollo_chado_username }}"
            password = "{{ apollo_chado_password }}"
            driverClassName = "org.postgresql.Driver"
            dialect = org.hibernate.dialect.PostgresPlusDialect
            url = "{{ apollo_chado_uri }}"
            properties {
                // See http://grails.org/doc/latest/guide/conf.html#dataSource for documentation
                jmxEnabled = true
                initialSize = 5
                maxActive = 50
                minIdle = 5
                maxIdle = 25
                maxWait = 10000
                maxAge = 10 * 60000
                timeBetweenEvictionRunsMillis = 5000
                minEvictableIdleTimeMillis = 60000
                validationQuery = "SELECT 1"
                validationQueryTimeout = 3
                validationInterval = 15000
                testOnBorrow = true
                testWhileIdle = true
                testOnReturn = false
                jdbcInterceptors = "ConnectionState"
                defaultTransactionIsolation = java.sql.Connection.TRANSACTION_READ_COMMITTED
            }
        }
    }
}

apollo {
    common_data_directory = "{{ apollo_data_directory }}"

    google_analytics = []

    admin {
        username = "{{ apollo_admin_username }}"
        password = "{{ apollo_admin_password }}"
        firstName = "{{ apollo_admin_firstname }}"
        lastName = "{{ apollo_admin_lastname }}"
    }

    authentications = [
        ["name":"Username Password Authenticator",
         "className":"usernamePasswordAuthenticatorService",
         "active":true,
        ]
        ,
        ["name":"Remote User Authenticator",
         "className":"remoteUserAuthenticatorService",
         "active":true,
        ]
    ]

    {{ apollo_config_apollo }}
}


{{ apollo_config_jbrowse }}
