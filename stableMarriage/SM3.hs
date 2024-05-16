{-# LANGUAGE TupleSections #-}

module Main where

import Data.Char (isDigit)
import Data.Maybe (isJust, fromMaybe)
import Data.List (sort, group)
import Data.Tuple.Extra ((***))
import Text.ParserCombinators.ReadP
import qualified Data.Map as Map
import System.Environment (getArgs)

type Person = String
type Pair = (Person, Person)
type Priority = Int
type PersonalPreferences = Map.Map Person Priority
type Preferences = Map.Map Person PersonalPreferences

-- Parse Data --

acceptGroupP, acceptIndivP, rejectIndivP :: ReadP [String]
acceptGroupP = char '[' *> munch1 isDigit `sepBy1` string " " <* char ']'
acceptIndivP = (: []) <$> munch1 isDigit
rejectIndivP = (: []) <$> string "-" <* munch1 isDigit

makePreferences :: Char -> String -> [[String]] -> (Person, PersonalPreferences)
makePreferences personType personId prefs
  | personType == 'm' = ('m' : personId, makePrefs $ makePersons 'w')
  | personType == 'w' = ('w' : personId, makePrefs $ makePersons 'm')
  | otherwise = error "Unknown person type"
  where
    makePersons prefix = map (map (prefix :)) $ filter (/= ["-"]) prefs
    makePrefs = Map.fromList . concat . zipWith (\x y -> map (, x) y) [1 ..]

prefListP :: ReadP (Person, PersonalPreferences)
prefListP = makePreferences
  <$> (char 'm' <++ char 'w')
  <*> munch1 isDigit <* string " :  "
  <*> ((acceptGroupP <++ acceptIndivP <++ rejectIndivP) `sepBy1` string " ")

parsePrefs :: String -> Preferences
parsePrefs =
  Map.fromList . map (fst . head . readP_to_S (prefListP <* eof)) . lines

mwPairP :: ReadP Pair    -- Pair = (w, m)
mwPairP = (\x y -> ('w' : y, 'm' : x))
  <$> (char 'm' *> munch1 isDigit <* string " ")
  <*> (char 'w' *> munch1 isDigit) <* option '\r' (char '\r')

wmPairP :: ReadP Pair    -- Pair = (w, m)
wmPairP = (\x y -> ('w' : x, 'm' : y))
  <$> (char 'w' *> munch1 isDigit <* string " ")
  <*> (char 'm' *> munch1 isDigit) <* option '\r' (char '\r')

parsePairs :: String -> [Pair]
parsePairs = map (fst . head . readP_to_S (mwPairP <++ wmPairP <* eof)) . lines

-- Tests --

-- V niektorom pare je osoba, ktora nema preferencny zoznam
test1 :: [Pair] -> Preferences -> String
test1 pairs prefs = case unknown $ concatMap (\(x, y) -> [x, y]) pairs of
    [] -> []
    xs -> "Unknown persons: " <> unwords xs
  where
    unknown = filter (`notElem` Map.keys prefs)

-- Niektora osoba je zaradena vo viacerych paroch
test2 :: [Pair] -> Preferences -> String
test2 pairs prefs = case redundant $ concatMap (\(x, y) -> [x, y]) pairs of
    [] -> []
    xs   -> "Redundant persons: " <> unwords xs
  where
    redundant = map head . filter ((/=1 ) . length) . group . sort

-- Nejaka osoba je sparovana s niekym, koho nema v preferencnom zozname
test3 :: [Pair] -> Preferences -> String
test3 pairs prefs = if null unaccepted
  then []
  else "Pairing with ignored person: " <> unwords unaccepted
  where
    testPair (x, y) =
      case (Map.lookup y $ prefs Map.! x, Map.lookup x $ prefs Map.! y) of
        (Just _, Just _)   -> []
        (Nothing, Just _)  -> [x]
        (Just _, Nothing)  -> [y]
        (Nothing, Nothing) -> [x, y]
    unaccepted = concatMap testPair pairs

-- zo zoznamu osob ys vyber tych, ktori akceptuju osobu x
accepting :: Person -> Preferences -> [Person] -> [Person]
accepting x prefs = filter (isJust . Map.lookup x . (prefs Map.!))

-- Nestabilny par kvoli potencialne preferovanejsiemu volnemu parterovi
test4 :: [Pair] -> Preferences -> String
test4 pairs prefs = if null unstablePersons
  then []
  else "Unstable persons in pairs: " <> unwords unstablePersons
  where
    testPair (x, y) = case (unstable x y, unstable y x) of
        (False, False) -> []
        (True, False)  -> [x]
        (False, True)  -> [y]
        (True, True)   -> [x, y]
    free = filter (`notElem` concatMap (\(x,y) -> [x,y]) pairs) $ Map.keys prefs
    unstable x y =
      any (\z -> getPriority prefs x z < prefs Map.! x Map.! y)
      $ accepting x prefs free
    unstablePersons = concatMap testPair pairs
    getPriority pref x y = fromMaybe 1000 $ Map.lookup y (pref Map.! x)

makePairs :: [a] -> [(a, a)]
makePairs = concat . go
  where
    go []  = []
    go [x] = []
    go (x : rest) = zip (repeat x) rest : go rest

rankPartners :: Preferences -> Person -> Person -> Person -> Ordering
rankPartners xPrefs x y posY = compare posYRank $ xPrefs Map.! x Map.! y
  where
    posYRank = fromMaybe 1000 $ Map.lookup posY (xPrefs Map.! x)

blockingPair :: (Pair, Pair) -> Preferences -> [String]
blockingPair ((a, b), (c, d)) prefs = bcTest <> adTest
  where
    bcTest = case (rankPartners prefs b a c, rankPartners prefs c d b) of
      (GT, _)  -> []
      (_, GT)  -> []
      (EQ, EQ) -> []
      (_, _)   -> [b <> "-" <> c]
    adTest = case (rankPartners prefs d c a, rankPartners prefs a b d) of
      (GT, _)  -> []
      (_, GT)  -> []
      (EQ, EQ) -> []
      (_, _)   -> [d <> "-" <> a]

-- Dvojica nestabilnych parov kvoli existencii blokujuceho paru
test5 :: [Pair] -> Preferences -> String
test5 pairs prefs = if null blocks
  then []
  else "Blocking pairs: " <> unwords blocks
  where
   blocks = concatMap (`blockingPair` prefs) $ makePairs pairs

testing :: [Pair] -> Preferences -> String
testing pairs prefs = makeTests [test1, test2, test3, test4, test5]
  where
    makeTests [] = "ok"
    makeTests (testFun : rest) = case testFun pairs prefs of
      []  -> makeTests rest
      msg -> msg

-- Evaluating --

happiness :: [Pair] -> Preferences -> Int
happiness pairs prefs = sum $ map hapPair pairs
  where
    hapPair (w, m) = prefs Map.! w Map.! m + prefs Map.! m Map.! w

egalitarian :: [Pair] -> Preferences -> Int
egalitarian pairs prefs = sum $ map hapPair pairs
  where
    hapPair (w, m) = prefs Map.! w Map.! m - prefs Map.! m Map.! w

evaluating :: [Pair] -> Preferences -> String
evaluating pairs prefs = numPairs <> "    " <> hapCost <> "    " <> egaCost
  where
    hapCost  = "Happiness Cost: " <> show (happiness pairs prefs)
    egaCost  = "Egalitarian Cost: " <> show (egalitarian pairs prefs)
    numPairs = "Number of pairs: " <> show (length pairs)

-- Entry point --

processing :: ([Pair], Preferences) -> String
processing (pairs, prefs) = if testResult /= "ok"
  then testResult
  else evaluating pairs prefs
  where
    testResult = testing pairs prefs

task filename1 filename2 = curry (parsePairs *** parsePrefs)
  <$> readFile filename1
  <*> readFile filename2

interactiveMain pairsFileName prefsFileName =
  processing <$> task pairsFileName prefsFileName

getFileNames :: IO (String, String)
getFileNames = do
  args <- getArgs
  return (head args, args !! 1)

main :: IO ()
main = do
  (pairsFileName, prefsFileName) <- getFileNames
  result <- interactiveMain pairsFileName prefsFileName
  print result
