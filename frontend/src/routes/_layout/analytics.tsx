import { Box, Container, Text, Button, Stack } from "@chakra-ui/react";
import { createFileRoute } from "@tanstack/react-router";
import { useAnalytics } from "@/hooks/useAnalytics";
import { Link } from "@tanstack/react-router";
import AnalyticsOverview from "@/components/Analytics/AnalyticsOverview";

export const Route = createFileRoute("/_layout/analytics")({
    component: Analytics,
});

function Analytics() {
    const { overview, isLoading, error, refetch } = useAnalytics({
        postedOnly: true,
    });

    if (isLoading) {
        return (
            <Container maxW="full">
                <Box pt={12} m={4}>
                    <Text>Loading analytics...</Text>
                </Box>
            </Container>
        );
    }

    if (error) {
        return (
            <Container maxW="full">
                <Box pt={12} m={4}>
                    <Text color="red">
                        Error loading analytics. Please try again.
                    </Text>
                </Box>
            </Container>
        );
    }

    return (
        <>
            <Container maxW="full">
                <Box pt={12} m={4}>
                    {overview?.total_posts === 0 ? (
                        <Stack align="center" justify="center">
                            You still haven't created any posts yet.
                            <Link to="/postings?generate=true">
                                <Button mt={4}>Let's get started!</Button>
                            </Link>
                        </Stack>
                    ) : (
                        <AnalyticsOverview data={overview} />
                    )}
                </Box>
            </Container>
        </>
    );
}
