import ldap from 'ldapjs';

const AD_LDAP_URL = process.env.AD_LDAP_URL || 'ldap://domain.com:389';
const AD_BASE_DN = process.env.AD_BASE_DN || 'DC=domain,DC=com';
const AD_ADMIN_DN = process.env.AD_ADMIN_DN || 'CN=Admin,CN=Users,DC=domain,DC=com';
const AD_ADMIN_PASSWORD = process.env.AD_ADMIN_PASSWORD || '';

export interface ADUser {
  dn: string;
  cn: string;
  sAMAccountName: string;
  userAccountControl: number;
}

function createClient(): ldap.Client {
  return ldap.createClient({
    url: AD_LDAP_URL,
    reconnect: true,
    timeout: 5000,
    connectTimeout: 10000,
  });
}

function adminBind(client: ldap.Client): Promise<void> {
  return new Promise((resolve, reject) => {
    client.bind(AD_ADMIN_DN, AD_ADMIN_PASSWORD, (err) => {
      if (err) {
        reject(new Error(`AD管理员绑定失败: ${err.message}`));
      } else {
        resolve();
      }
    });
  });
}

function userSearch(client: ldap.Client, userId: string): Promise<ADUser | null> {
  return new Promise((resolve, reject) => {
    const searchFilter = `(|(sAMAccountName=${userId})(userPrincipalName=${userId}*))`;
    
    client.search(AD_BASE_DN, {
      scope: 'sub',
      filter: searchFilter,
      attributes: ['dn', 'cn', 'sAMAccountName', 'userAccountControl'],
    }, (err, res) => {
      if (err) {
        reject(new Error(`AD用户搜索失败: ${err.message}`));
        return;
      }

      let user: ADUser | null = null;

      res.on('searchEntry', (entry) => {
        const obj = entry.pojo;
        user = {
          dn: obj.objectName,
          cn: obj.attributes.find((a) => a.type === 'cn')?.values[0] || '',
          sAMAccountName: obj.attributes.find((a) => a.type === 'sAMAccountName')?.values[0] || '',
          userAccountControl: parseInt(
            obj.attributes.find((a) => a.type === 'userAccountControl')?.values[0] || '0',
            10
          ),
        };
      });

      res.on('error', (err) => {
        reject(new Error(`AD搜索错误: ${err.message}`));
      });

      res.on('end', () => {
        resolve(user);
      });
    });
  });
}

function changePassword(client: ldap.Client, userDn: string, newPassword: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const entry = {
      unicodePwd: Buffer.from(`"${newPassword}"`, 'utf16le'),
    };

    client.modify(userDn, [
      new ldap.Change({
        operation: 'delete',
        modification: {
          type: 'unicodePwd',
          values: [Buffer.from('"unused"', 'utf16le')],
        },
      }),
    ], (err) => {
      if (err) {
        console.log('第一次修改（删除）错误，尝试直接添加:', err.message);
      }
    });

    client.modify(userDn, [
      new ldap.Change({
        operation: 'add',
        modification: {
          type: 'unicodePwd',
          values: [Buffer.from(`"${newPassword}"`, 'utf16le')],
        },
      }),
    ], (err) => {
      if (err) {
        reject(new Error(`密码修改失败: ${err.message}`));
      } else {
        resolve();
      }
    });
  });
}

export async function resetAdPassword(userId: string, newPassword: string): Promise<{ success: boolean; message: string }> {
  const client = createClient();

  return new Promise((resolve) => {
    client.on('error', (err) => {
      console.error('LDAP Client Error:', err);
      resolve({ success: false, message: `LDAP连接错误: ${err.message}` });
    });

    adminBind(client)
      .then(() => userSearch(client, userId))
      .then((user) => {
        if (!user) {
          client.unbind();
          resolve({ success: false, message: '未找到AD用户' });
          return null;
        }
        return changePassword(client, user.dn, newPassword)
          .then(() => {
            client.unbind();
            return { success: true, message: '密码重置成功' };
          });
      })
      .then((result) => {
        if (result) {
          resolve(result);
        }
      })
      .catch((error) => {
        try {
          client.unbind();
        } catch {}
        resolve({ success: false, message: error.message });
      });
  });
}
