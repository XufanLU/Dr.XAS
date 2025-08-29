import databases from './databases.json'


export type Databases = typeof databases
export type DatabaseId = keyof Databases
export type DatabaseConfig = Databases[DatabaseId]

export default databases

export function checkDatabases(databases: Databases) {
    return "success"
}