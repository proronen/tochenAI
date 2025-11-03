import { useEffect, useState } from "react";
import {
    Box,
    Heading,
    Text,
    Textarea,
    Input,
    Button,
    VStack,
    HStack,
    Badge,
} from "@chakra-ui/react";
import {
    getAllUsers,
    updateClientSpecifics,
    getLLMUsageSummary,
} from "@/client/core/request";
import { Field } from "@/components/ui/field";
import useCustomToast from "@/hooks/useCustomToast";

interface User {
    id: string;
    email: string;
    full_name?: string;
    quota: number;
    usage_count: number;
    business_description?: string;
    client_avatars?: string;
    is_superuser: boolean;
}

interface LLMUsageSummary {
    total_requests: number;
    total_tokens: number;
    total_cost_usd: number;
    requests_by_provider: Record<string, number>;
    requests_by_type: Record<string, number>;
}

export default function ClientSpecifics() {
    const [users, setUsers] = useState<User[]>([]);
    const [usageSummaries, setUsageSummaries] = useState<
        Record<string, LLMUsageSummary>
    >({});
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState<Record<string, Partial<User>>>({});
    const { showSuccessToast } = useCustomToast();

    useEffect(() => {
        setLoading(true);
        getAllUsers()
            .then((data) => {
                setUsers(data.data);
                // Fetch usage summaries for each user
                return Promise.all(
                    data.data.map(async (user: User) => {
                        try {
                            const summary = await getLLMUsageSummary(user.id);
                            return { userId: user.id, summary };
                        } catch (e) {
                            console.error(
                                `Failed to fetch usage for user ${user.id}:`,
                                e,
                            );
                            return { userId: user.id, summary: null };
                        }
                    }),
                );
            })
            .then((summaries) => {
                const summaryMap: Record<string, LLMUsageSummary> = {};
                summaries.forEach(({ userId, summary }) => {
                    if (summary) {
                        summaryMap[userId] = summary;
                    }
                });
                setUsageSummaries(summaryMap);
            })
            .finally(() => setLoading(false));
    }, []);

    const handleChange = (userId: string, field: keyof User, value: any) => {
        setForm((prev) => ({
            ...prev,
            [userId]: {
                ...prev[userId],
                [field]: value,
            },
        }));
    };

    const handleSubmit = async (user: User) => {
        setLoading(true);
        try {
            await updateClientSpecifics(user.id, form[user.id]!);
            showSuccessToast("Client specifics updated successfully");
        } catch (e) {
            console.error("Error updating user:", e);
        } finally {
            setLoading(false);
        }
    };

    const formatCost = (cost: number) => {
        return `$${cost.toFixed(4)}`;
    };

    const formatTokens = (tokens: number) => {
        if (tokens >= 1000000) {
            return `${(tokens / 1000000).toFixed(1)}M`;
        } else if (tokens >= 1000) {
            return `${(tokens / 1000).toFixed(1)}K`;
        }
        return tokens.toString();
    };

    return (
        <Box>
            <Heading size="md" mb={6}>
                Client Specifics
            </Heading>
            {users
                .filter((u) => !u.is_superuser)
                .map((user) => {
                    const usage = usageSummaries[user.id];
                    return (
                        <Box
                            key={user.id}
                            p={4}
                            mb={8}
                            borderWidth={1}
                            borderRadius="md"
                        >
                            <Text fontWeight="bold">
                                {user.full_name || user.email}
                            </Text>

                            {/* LLM Usage Summary */}
                            {usage && (
                                <Box
                                    mt={3}
                                    p={3}
                                    bg="gray.50"
                                    borderRadius="md"
                                >
                                    <Text fontWeight="semibold" mb={2}>
                                        LLM Usage Summary
                                    </Text>
                                    <HStack spacing={4} wrap="wrap">
                                        <Badge colorScheme="blue">
                                            Requests: {usage.total_requests}
                                        </Badge>
                                        <Badge colorScheme="green">
                                            Tokens:{" "}
                                            {formatTokens(usage.total_tokens)}
                                        </Badge>
                                        <Badge colorScheme="purple">
                                            Cost:{" "}
                                            {formatCost(usage.total_cost_usd)}
                                        </Badge>
                                    </HStack>
                                    {Object.keys(usage.requests_by_provider)
                                        .length > 0 && (
                                        <Text
                                            fontSize="sm"
                                            mt={2}
                                            color="gray.600"
                                        >
                                            Providers:{" "}
                                            {Object.entries(
                                                usage.requests_by_provider,
                                            )
                                                .map(
                                                    ([provider, count]) =>
                                                        `${provider}: ${count}`,
                                                )
                                                .join(", ")}
                                        </Text>
                                    )}
                                </Box>
                            )}

                            <VStack gap={3} mt={2}>
                                <Field label="Quota">
                                    {users.filter((u) => u.is_superuser)
                                        .length === 0 ? (
                                        <Text>{user.quota}</Text>
                                    ) : (
                                        <Input
                                            type="number"
                                            min={0}
                                            value={
                                                form[user.id]?.quota ??
                                                user.quota
                                            }
                                            onChange={(e) =>
                                                handleChange(
                                                    user.id,
                                                    "quota",
                                                    parseInt(e.target.value) ||
                                                        0,
                                                )
                                            }
                                        />
                                    )}
                                </Field>
                                <Field label="Usage Count">
                                    <Text>{user.usage_count}</Text>
                                </Field>
                                <Field label="Business Description">
                                    <Textarea
                                        value={
                                            form[user.id]
                                                ?.business_description ??
                                            (user.business_description || "")
                                        }
                                        onChange={(e) =>
                                            handleChange(
                                                user.id,
                                                "business_description",
                                                e.target.value,
                                            )
                                        }
                                    />
                                </Field>
                                <Field label="Client Avatars">
                                    <Textarea
                                        value={
                                            form[user.id]?.client_avatars ??
                                            (user.client_avatars || "")
                                        }
                                        onChange={(e) =>
                                            handleChange(
                                                user.id,
                                                "client_avatars",
                                                e.target.value,
                                            )
                                        }
                                    />
                                </Field>
                                <Button
                                    colorScheme="blue"
                                    onClick={() => handleSubmit(user)}
                                    isLoading={loading}
                                >
                                    Save
                                </Button>
                            </VStack>
                        </Box>
                    );
                })}
            {users.filter((u) => !u.is_superuser).length === 0 && (
                <Text>No clients found.</Text>
            )}
        </Box>
    );
}
