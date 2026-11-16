class Settings {
    constructor() {
        this.configPath = 'static/config.json';
        this.sessionsDir = 'sessions';
        this.plansDir = 'static/plans';
    }

    async getSetting(key) {
        try {
            const response = await fetch(this.configPath);
            const config = await response.json();
            return config[key] !== undefined ? config[key] : null;
        } catch (error) {
            console.error('Error reading config:', error);
            return null;
        }
    }

    async setSetting(key, value) {
        try {
            const response = await fetch('/update-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key, value })
            });
            return response.ok;
        } catch (error) {
            console.error('Error updating config:', error);
            return false;
        }
    }

    async getSessionInfo(key) {
        try {
            const currentSessionName = await this.getSetting('session');
            const currentSessionNameCleaned = currentSessionName.replace('.json', '');
            const response = await fetch(`${this.plansDir}/${currentSessionNameCleaned}_plans/info.json`);
            const config = await response.json();
            return config[key] !== undefined ? config[key] : null;

        } catch (error) {
            console.error('Error reading info:', error);
            return null;
        }
    }

    async setSessionInfo(key, value) {
        try {
            const response = await fetch('/update-session-info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key, value })
            });
            return response.ok;
        } catch (error) {
            console.error('Error updating info:', error);
            return false;
        }
    }

    async renameSessionFile(newName) {
        try {
            const currentSession = await this.getSetting('session');
            const oldPath = `${this.sessionsDir}/${currentSession}`;
            const newPath = `${this.sessionsDir}/${newName}.json`;

            const response = await fetch('/rename-file', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ oldPath, newPath })
            });

            if (response.ok) {
                console.log(`Successfully renamed session to '${newName}'`);
                return true;
            } else {
                throw new Error((await response.json()).message);
            }
        } catch (error) {
            console.error(`Error renaming session file: ${error.message}`);
            return false;
        }
    }

    async renamePlanFolder(newName) {
        try {
            const sessionName = (await this.getSetting('session')).replace('.json', '');
            const oldFolder = `${this.plansDir}/${sessionName}_plans`;
            const newFolder = `${this.plansDir}/${newName}_plans`;

            const response = await fetch('/rename-folder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ oldPath: oldFolder, newPath: newFolder })
            });

            if (response.ok) {
                console.log(`Successfully renamed plan folder to '${newName}_plans/'`);
                return true;
            } else {
                throw new Error((await response.json()).message);
            }
        } catch (error) {
            console.error(`Error renaming plan folder: ${error.message}`);
            return false;
        }
    }

    async newSession(sessionName) {
        try {
            const sessionFilePath = `${this.sessionsDir}/${sessionName}.json`;
            const plansPath = `${this.plansDir}/${sessionName}_plans`;

            const sessionExists = await this._checkPathExists(sessionFilePath);
            const plansExist = await this._checkPathExists(plansPath);

            if (sessionExists || plansExist) {
                console.log(`Session '${sessionName}' already exists.`);
                return false;
            }

            await this._createFile(sessionFilePath, '[]');
            await this._createDirectory(plansPath);

            const planFiles = ['summary.md', 'recon_plan.md', 'va_plan.md', 'exploit_plan.md'];
            for (const file of planFiles) {
                await this._createFile(`${plansPath}/${file}`, '');
            }

            const infoData = { stage: "recon-planning", report: false, time: 0 };
            await this._createFile(`${plansPath}/info.json`, JSON.stringify(infoData, null, 2));

            console.log(`Created new session: ${sessionName}`);
            return true;
        } catch (error) {
            console.error(`Unexpected error during session creation: ${error.message}`);
            return false;
        }
    }

    async deleteSession() {
        try {
            const sessionFile = await this.getSetting('session');
            if (!sessionFile) return false;

            const cleanName = sessionFile.replace('.json', '');
            const sessionPath = `${this.sessionsDir}/${sessionFile}`;
            const plansFolder = `${this.plansDir}/${cleanName}_plans`;

            if (await this._checkPathExists(sessionPath)) {
                await this._deleteFile(sessionPath);
            }

            if (await this._checkPathExists(plansFolder)) {
                await this._deleteDirectory(plansFolder);
            }

            return true;
        } catch (error) {
            console.error(`Unexpected error during session deletion: ${error.message}`);
            return false;
        }
    }

    async fallbackSession() {
        try {
            const response = await fetch('/get-sessions');
            const data = await response.json();
            const sessions = data.sessions || [];

            if (sessions.length > 0) {
                const firstFile = sessions[0];
                await this.setSetting('session', firstFile);
                console.log(`Fallback to session: ${firstFile}`);
                return firstFile;
            }
            return null;
        } catch (error) {
            console.error(`Error in fallback session: ${error.message}`);
            throw error;
        }
    }

    // === Internal Helpers ===
    async _checkPathExists(path) {
        try {
            const response = await fetch(`/check-path?path=${encodeURIComponent(path)}`);
            const data = await response.json();
            return data.exists;
        } catch (error) {
            console.error(`Error checking path ${path}:`, error);
            return false;
        }
    }

    async _createFile(path, content) {
        try {
            const response = await fetch('/create-file', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path, content })
            });
            return response.ok;
        } catch (error) {
            console.error(`Error creating file ${path}:`, error);
            throw error;
        }
    }

    async _createDirectory(path) {
        try {
            const response = await fetch('/create-directory', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            });
            return response.ok;
        } catch (error) {
            console.error(`Error creating directory ${path}:`, error);
            throw error;
        }
    }

    async _deleteFile(path) {
        try {
            const response = await fetch('/delete-file', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            });
            return response.ok;
        } catch (error) {
            console.error(`Error deleting file ${path}:`, error);
            throw error;
        }
    }

    async _deleteDirectory(path) {
        try {
            const response = await fetch('/delete-directory', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            });
            return response.ok;
        } catch (error) {
                console.error(`Error deleting directory ${path}:`, error);
                throw error;
        }
    }
}

export default Settings;
