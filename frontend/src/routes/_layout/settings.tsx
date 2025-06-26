import { Container, Heading, Tabs } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"

import Appearance from "@/components/UserSettings/Appearance"
import ChangePassword from "@/components/UserSettings/ChangePassword"
import DeleteAccount from "@/components/UserSettings/DeleteAccount"
import UserInformation from "@/components/UserSettings/UserInformation"
import SocialMediaAccounts from "@/components/UserSettings/SocialMediaAccounts"
import ClientSpecifics from "@/components/UserSettings/ClientSpecifics"
import useAuth from "@/hooks/useAuth"

const tabsConfig = [
  { value: "my-profile", title: "My profile", component: UserInformation },
  { is_superuser: true, value: "password", title: "Password", component: ChangePassword },
  { value: "appearance", title: "Appearance", component: Appearance },
  { value: "social-media", title: "Social Media Accounts", component: SocialMediaAccounts },
  { is_superuser: true, value: "client-specifics", title: "Client Specifics", component: ClientSpecifics },
  { is_superuser: true, value: "danger-zone", title: "Danger zone", component: DeleteAccount },
]

export const Route = createFileRoute("/_layout/settings")({
  component: UserSettings,
})

function UserSettings() {
  const { user: currentUser } = useAuth()
  const finalTabs = currentUser?.is_superuser
    ? tabsConfig
    : tabsConfig.filter(item => !item.is_superuser)

  if (!currentUser) {
    return null
  }

  return (
    <Container maxW="full">
      <Heading size="lg" textAlign={{ base: "center", md: "left" }} py={12}>
        User Settings
      </Heading>

      <Tabs.Root defaultValue="my-profile" variant="subtle">
        <Tabs.List>
          {finalTabs.map((tab) => (
            <Tabs.Trigger key={tab.value} value={tab.value}>
              {tab.title}
            </Tabs.Trigger>
          ))}
        </Tabs.List>
        {finalTabs.map((tab) => (
          <Tabs.Content key={tab.value} value={tab.value}>
            <tab.component />
          </Tabs.Content>
        ))}
      </Tabs.Root>
    </Container>
  )
}
