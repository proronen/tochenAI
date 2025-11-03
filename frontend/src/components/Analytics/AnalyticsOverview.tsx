import { AnalyticsGetOverviewResponse } from "@/client/types.gen";
import { Container, Heading, Box, Text, HStack } from "@chakra-ui/react";

interface AnalyticsOverviewProps {
    data?: AnalyticsGetOverviewResponse;
}

const AnalyticsOverview = ({ data }: AnalyticsOverviewProps) => {
    if (!data) {
        return;
    }

    const statusEntries = Object.entries(data.status_breakdown || {});

    return (
        <Container maxW="full">
            <Heading size="sm" py={4}>
                Analytics Overview
            </Heading>
            {statusEntries.map(([status, count]) => (
                <Box key={status} p={2} mb={2}>
                    <HStack>
                        <Text fontWeight="bold">{status}:</Text>
                        <Text>{count}</Text>
                    </HStack>
                </Box>
            ))}
        </Container>
    );
};

export default AnalyticsOverview;
