import React from 'react';
import { Button, Space, Tooltip, Typography } from 'antd';
import { 
  DesktopOutlined, 
  DatabaseOutlined, 
  GlobalOutlined, 
  SafetyOutlined,
  ReloadOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';

const { Text } = Typography;

interface QuickCommandsProps {
  onExecuteCommand: (command: string) => void;
  isConnected: boolean;
}

const QuickCommands: React.FC<QuickCommandsProps> = ({ onExecuteCommand, isConnected }) => {
  const quickCommands = [
    {
      name: 'Système',
      commands: [
        { label: 'Uptime', command: 'uptime', icon: <DesktopOutlined /> },
        { label: 'Processus', command: 'ps aux', icon: <DesktopOutlined /> },
        { label: 'Mémoire', command: 'free -h', icon: <DesktopOutlined /> },
        { label: 'Espace disque', command: 'df -h', icon: <DesktopOutlined /> },
      ]
    },
    {
      name: 'Réseau',
      commands: [
        { label: 'Interfaces', command: 'ip addr show', icon: <GlobalOutlined /> },
        { label: 'Connexions', command: 'netstat -tuln', icon: <GlobalOutlined /> },
        { label: 'Ping localhost', command: 'ping -c 4 localhost', icon: <GlobalOutlined /> },
        { label: 'DNS', command: 'cat /etc/resolv.conf', icon: <GlobalOutlined /> },
      ]
    },
    {
      name: 'Sécurité',
      commands: [
        { label: 'Utilisateurs', command: 'who', icon: <SafetyOutlined /> },
        { label: 'Sessions SSH', command: 'who', icon: <SafetyOutlined /> },
        { label: 'Logs auth', command: 'tail -20 /var/log/auth.log', icon: <SafetyOutlined /> },
        { label: 'Permissions', command: 'ls -la /etc/passwd /etc/shadow', icon: <SafetyOutlined /> },
      ]
    },
    {
      name: 'Services',
      commands: [
        { label: 'Services actifs', command: 'systemctl list-units --type=service --state=active', icon: <DatabaseOutlined /> },
        { label: 'SSH Status', command: 'systemctl status ssh', icon: <DatabaseOutlined /> },
        { label: 'Firewall Status', command: 'systemctl status ufw', icon: <DatabaseOutlined /> },
        { label: 'Redémarrer SSH', command: 'sudo systemctl restart ssh', icon: <ReloadOutlined /> },
      ]
    }
  ];

  const handleCommandClick = (command: string) => {
    if (!isConnected) {
      return;
    }
    onExecuteCommand(command);
  };

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ marginBottom: 8 }}>
        <Text strong>Commandes rapides :</Text>
        {!isConnected && (
          <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
            (Connectez-vous d'abord au terminal)
          </Text>
        )}
      </div>
      
      {quickCommands.map((category, categoryIndex) => (
        <div key={categoryIndex} style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 'bold' }}>
            {category.name}:
          </Text>
          <Space wrap style={{ marginTop: 4 }}>
            {category.commands.map((cmd, cmdIndex) => (
              <Tooltip 
                key={cmdIndex} 
                title={`Exécuter: ${cmd.command}`}
                placement="top"
              >
                <Button
                  size="small"
                  icon={cmd.icon}
                  onClick={() => handleCommandClick(cmd.command)}
                  disabled={!isConnected}
                  style={{ fontSize: 11 }}
                >
                  {cmd.label}
                </Button>
              </Tooltip>
            ))}
          </Space>
        </div>
      ))}
      
      <div style={{ marginTop: 8, padding: 8, backgroundColor: '#f5f5f5', borderRadius: 4 }}>
        <Text type="secondary" style={{ fontSize: 11 }}>
          <InfoCircleOutlined style={{ marginRight: 4 }} />
          Ces commandes sont des raccourcis pour les opérations courantes. 
          Vous pouvez aussi saisir vos propres commandes dans le terminal.
        </Text>
      </div>
    </div>
  );
};

export default QuickCommands;
