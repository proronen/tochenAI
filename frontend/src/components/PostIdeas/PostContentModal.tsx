import { useState } from "react";
import { Box, Text, Textarea, Button, VStack, HStack } from "@chakra-ui/react";
import {
    DialogRoot,
    DialogContent,
    DialogHeader,
    DialogBody,
    DialogFooter,
    DialogCloseTrigger,
} from "../ui/dialog";
import { Field } from "../ui/field";
import {
    generatePostContent,
    createPosting,
    generateHashtags,
    generateImage,
} from "../../client/core/request";
import useAuth from "../../hooks/useAuth";
import useCustomToast from "../../hooks/useCustomToast";

interface PostContentModalProps {
    isOpen: boolean;
    onClose: () => void;
    postIdea: {
        id: string;
        text: string;
        isActive: boolean;
    };
    onPostCreated: () => void;
}

interface GeneratedContent {
    post_text: string;
    image_description: string;
}

export default function PostContentModal({
    isOpen,
    onClose,
    postIdea,
    onPostCreated,
}: PostContentModalProps) {
    const [generatedContent, setGeneratedContent] =
        useState<GeneratedContent | null>(null);
    const [loading, setLoading] = useState(false);
    const [regeneratingText, setRegeneratingText] = useState(false);
    const [regeneratingImage, setRegeneratingImage] = useState(false);
    const [saving, setSaving] = useState(false);
    const { user } = useAuth();
    const { showSuccessToast, showErrorToast } = useCustomToast();

    const handleGenerateContent = async () => {
        if (!user?.business_description) {
            showErrorToast("Business description is required");
            return;
        }

        setLoading(true);
        try {
            const result = await generatePostContent(
                postIdea.text,
                user.business_description,
                user.client_avatars ?? undefined,
            );

            setGeneratedContent(result);
            showSuccessToast("Post content generated successfully!");
        } catch (error) {
            showErrorToast("Failed to generate post content");
        } finally {
            setLoading(false);
        }
    };

    const handleRegenerateText = async () => {
        if (!user?.business_description) return;

        setRegeneratingText(true);
        try {
            const result = await generatePostContent(
                postIdea.text,
                user.business_description,
                user.client_avatars ?? undefined,
            );

            setGeneratedContent((prev) => ({
                ...prev!,
                post_text: result.post_text,
            }));
            showSuccessToast("Post text regenerated!");
        } catch (error) {
            showErrorToast("Failed to regenerate post text");
        } finally {
            setRegeneratingText(false);
        }
    };

    const handleRegenerateImage = async () => {
        if (!user?.business_description) return;

        setRegeneratingImage(true);
        try {
            const result = await generatePostContent(
                postIdea.text,
                user.business_description,
                user.client_avatars ?? undefined,
            );

            setGeneratedContent((prev) => ({
                ...prev!,
                image_description: result.image_description,
            }));
            showSuccessToast("Image description regenerated!");
        } catch (error) {
            showErrorToast("Failed to regenerate image description");
        } finally {
            setRegeneratingImage(false);
        }
    };

    const handleSavePost = async () => {
        if (!generatedContent) return;

        setSaving(true);
        try {
            // Generate hashtags for the post content
            let hashtags = "";
            try {
                const hashtagResult = await generateHashtags(
                    generatedContent.post_text,
                    "general",
                    5,
                );
                hashtags = hashtagResult.hashtags.join(", ");
            } catch (error) {
                console.warn(
                    "Failed to generate hashtags, using empty hashtags",
                );
            }

            // Generate real image using the image description
            let imageUrl = "";
            try {
                const imageResult = await generateImage(
                    generatedContent.image_description,
                    "1024x1024",
                    "standard",
                );
                imageUrl = imageResult.image_url;
            } catch (error) {
                console.warn("Failed to generate image, using placeholder");
                // Fallback to placeholder image
                imageUrl = `https://via.placeholder.com/800x600/4A90E2/FFFFFF?text=${encodeURIComponent(generatedContent.image_description || "Generated Image")}`;
            }

            // Create the actual posting
            await createPosting({
                media_url: imageUrl,
                text: generatedContent.post_text,
                hashtags: hashtags,
                scheduled_time: new Date(
                    Date.now() + 24 * 60 * 60 * 1000,
                ).toISOString(), // Tomorrow
                to_facebook: true,
                to_instagram: true,
                to_tiktok: true,
            });

            showSuccessToast("Post saved successfully!");
            onPostCreated();
            onClose();
        } catch (error) {
            showErrorToast("Failed to save post");
        } finally {
            setSaving(false);
        }
    };

    return (
        <DialogRoot
            open={isOpen}
            onOpenChange={({ open }) => !open && onClose()}
        >
            <DialogContent>
                <DialogHeader>Generate Post Content</DialogHeader>
                <DialogBody>
                    <VStack gap={4} alignItems="stretch">
                        <Box p={3} bg="blue.50" borderRadius="md">
                            <Text fontWeight="semibold" mb={2}>
                                Selected Post Idea:
                            </Text>
                            <Text>{postIdea.text}</Text>
                        </Box>

                        {!generatedContent ? (
                            <Button
                                onClick={handleGenerateContent}
                                loading={loading}
                                colorScheme="blue"
                                size="lg"
                            >
                                Generate Post Content
                            </Button>
                        ) : (
                            <VStack gap={4} alignItems="stretch">
                                <Field label="Post Text">
                                    <VStack gap={2} alignItems="stretch">
                                        <Textarea
                                            value={generatedContent.post_text}
                                            readOnly
                                            rows={4}
                                        />
                                        <Button
                                            onClick={handleRegenerateText}
                                            loading={regeneratingText}
                                            size="sm"
                                            variant="outline"
                                            colorScheme="blue"
                                        >
                                            Regenerate Text
                                        </Button>
                                    </VStack>
                                </Field>

                                <Field label="Image Description">
                                    <VStack gap={2} alignItems="stretch">
                                        <Textarea
                                            value={
                                                generatedContent.image_description
                                            }
                                            readOnly
                                            rows={2}
                                        />
                                        <Button
                                            onClick={handleRegenerateImage}
                                            loading={regeneratingImage}
                                            size="sm"
                                            variant="outline"
                                            colorScheme="blue"
                                        >
                                            Regenerate Image
                                        </Button>
                                    </VStack>
                                </Field>

                                <HStack justify="space-between">
                                    <Button
                                        onClick={handleSavePost}
                                        loading={saving}
                                        colorScheme="green"
                                    >
                                        Save Post
                                    </Button>
                                    <Button
                                        onClick={handleGenerateContent}
                                        loading={loading}
                                        variant="outline"
                                        colorScheme="blue"
                                    >
                                        Regenerate All
                                    </Button>
                                </HStack>
                            </VStack>
                        )}
                    </VStack>
                </DialogBody>
                <DialogFooter>
                    <DialogCloseTrigger asChild>
                        <Button variant="subtle" colorPalette="gray">
                            Close
                        </Button>
                    </DialogCloseTrigger>
                </DialogFooter>
            </DialogContent>
        </DialogRoot>
    );
}
