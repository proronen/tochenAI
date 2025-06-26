import { Box, Button, HStack, Text } from "@chakra-ui/react";

// TODO: make real oAuth connections
const SOCIALS = [
  { name: "Facebook", url: "/api/v1/auth/facebook/login" },
  { name: "Instagram", url: "/api/v1/auth/facebook/login" }, // Instagram uses Facebook OAuth
  { name: "TikTok", url: "/api/v1/auth/tiktok/login" },
];

const SocialMediaAccounts = () => (
  <Box p={4}>
    <Text fontSize="lg" mb={4}>Connect your social media accounts:</Text>
    <HStack gap={4}>
      {SOCIALS.map((s) => (
        <Button
          as="a"
          href={s.url}
          target="_blank"
          rel="noopener noreferrer"
          key={s.name}
          colorScheme="blue"
        >
          Connect {s.name}
        </Button>
      ))}
    </HStack>
  </Box>
);

export default SocialMediaAccounts; 